using System;
using System.Net;
using System.Text;
using System.Threading;
using UnityEngine;

/// <summary>
/// Auto-start HTTP server that exposes Unity camera frames.
/// No manual GameObject binding required.
///
/// Endpoints:
///   GET /frame.jpg    -> latest JPEG frame (single snapshot)
///   GET /stream.mjpg  -> live MJPEG stream
///   GET /healthz      -> ok
///
/// Default URL: http://<host>:18082/frame.jpg
/// </summary>
public class UnityCameraHttpServer : MonoBehaviour
{
    [Header("Network")]
    public int port = 18082;
    [Range(1, 30)] public int fps = 10;
    [Range(30, 95)] public int jpegQuality = 75;

    [Header("Capture")]
    public int width = 640;
    public int height = 360;

    private static byte[] s_latestJpeg;
    private static readonly object s_frameLock = new object();

    private Camera _targetCamera;
    private RenderTexture _rt;
    private Texture2D _readTex;

    private HttpListener _listener;
    private Thread _httpThread;
    private volatile bool _running;

    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void AutoCreate()
    {
        if (FindAnyObjectByType<UnityCameraHttpServer>() != null)
            return;

        var go = new GameObject("UnityCameraHttpServer_Auto");
        DontDestroyOnLoad(go);
        go.AddComponent<UnityCameraHttpServer>();
    }

    void Start()
    {
        _targetCamera = Camera.main;
        if (_targetCamera == null)
        {
            Debug.LogError("UnityCameraHttpServer: No MainCamera found. Tag one camera as MainCamera.");
            enabled = false;
            return;
        }

        _rt = new RenderTexture(width, height, 16, RenderTextureFormat.ARGB32);
        _readTex = new Texture2D(width, height, TextureFormat.RGB24, false);

        StartHttpServer();
        InvokeRepeating(nameof(CaptureFrame), 0.1f, 1f / Mathf.Max(1, fps));

        Debug.Log($"UnityCameraHttpServer running: http://0.0.0.0:{port}/frame.jpg");
    }

    void OnDestroy()
    {
        StopHttpServer();
        CancelInvoke(nameof(CaptureFrame));

        if (_rt != null) _rt.Release();
        if (_readTex != null) Destroy(_readTex);
    }

    void CaptureFrame()
    {
        if (_targetCamera == null) return;

        var prev = _targetCamera.targetTexture;
        var prevActive = RenderTexture.active;

        _targetCamera.targetTexture = _rt;
        _targetCamera.Render();

        RenderTexture.active = _rt;
        _readTex.ReadPixels(new Rect(0, 0, width, height), 0, 0);
        _readTex.Apply(false, false);

        byte[] jpg = _readTex.EncodeToJPG(jpegQuality);
        lock (s_frameLock)
        {
            s_latestJpeg = jpg;
        }

        _targetCamera.targetTexture = prev;
        RenderTexture.active = prevActive;
    }

    void StartHttpServer()
    {
        try
        {
            _listener = new HttpListener();
            _listener.Prefixes.Add($"http://*:{port}/");
            _listener.Start();

            _running = true;
            _httpThread = new Thread(HttpLoop) { IsBackground = true };
            _httpThread.Start();
        }
        catch (Exception ex)
        {
            Debug.LogError($"UnityCameraHttpServer failed to start HTTP listener on port {port}: {ex.Message}");
        }
    }

    void StopHttpServer()
    {
        _running = false;
        try { _listener?.Stop(); } catch { }
        try { _listener?.Close(); } catch { }
        try { _httpThread?.Join(200); } catch { }
    }

    void HttpLoop()
    {
        while (_running && _listener != null && _listener.IsListening)
        {
            HttpListenerContext ctx = null;
            try
            {
                ctx = _listener.GetContext();
                HandleRequest(ctx);
            }
            catch (HttpListenerException)
            {
                break;
            }
            catch (ObjectDisposedException)
            {
                break;
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"UnityCameraHttpServer request error: {ex.Message}");
                if (ctx != null)
                {
                    try { ctx.Response.StatusCode = 500; ctx.Response.Close(); } catch { }
                }
            }
        }
    }

    static void HandleRequest(HttpListenerContext ctx)
    {
        string path = ctx.Request.Url.AbsolutePath;

        if (path.Equals("/healthz", StringComparison.OrdinalIgnoreCase))
        {
            byte[] ok = Encoding.UTF8.GetBytes("ok");
            ctx.Response.StatusCode = 200;
            ctx.Response.ContentType = "text/plain";
            ctx.Response.ContentLength64 = ok.Length;
            ctx.Response.OutputStream.Write(ok, 0, ok.Length);
            ctx.Response.Close();
            return;
        }

        if (path.Equals("/stream.mjpg", StringComparison.OrdinalIgnoreCase))
        {
            const string boundary = "frame";
            ctx.Response.StatusCode = 200;
            ctx.Response.ContentType = $"multipart/x-mixed-replace; boundary={boundary}";
            ctx.Response.SendChunked = true;
            ctx.Response.AddHeader("Cache-Control", "no-cache, no-store, must-revalidate");
            ctx.Response.AddHeader("Pragma", "no-cache");
            ctx.Response.AddHeader("Expires", "0");
            ctx.Response.AddHeader("Access-Control-Allow-Origin", "*");

            try
            {
                while (true)
                {
                    byte[] frame;
                    lock (s_frameLock)
                    {
                        frame = s_latestJpeg;
                    }

                    if (frame != null)
                    {
                        string header =
                            $"--{boundary}\r\n" +
                            "Content-Type: image/jpeg\r\n" +
                            $"Content-Length: {frame.Length}\r\n\r\n";

                        byte[] headerBytes = Encoding.ASCII.GetBytes(header);
                        ctx.Response.OutputStream.Write(headerBytes, 0, headerBytes.Length);
                        ctx.Response.OutputStream.Write(frame, 0, frame.Length);
                        byte[] newline = Encoding.ASCII.GetBytes("\r\n");
                        ctx.Response.OutputStream.Write(newline, 0, newline.Length);
                        ctx.Response.OutputStream.Flush();
                    }

                    Thread.Sleep(1000 / 10); // 10 fps stream pacing
                }
            }
            catch
            {
                // Client disconnected; safely end response.
            }
            finally
            {
                try { ctx.Response.Close(); } catch { }
            }
            return;
        }

        if (path.Equals("/frame.jpg", StringComparison.OrdinalIgnoreCase))
        {
            byte[] frame;
            lock (s_frameLock)
            {
                frame = s_latestJpeg;
            }

            if (frame == null)
            {
                byte[] noFrame = Encoding.UTF8.GetBytes("no frame yet");
                ctx.Response.StatusCode = 503;
                ctx.Response.ContentType = "text/plain";
                ctx.Response.ContentLength64 = noFrame.Length;
                ctx.Response.OutputStream.Write(noFrame, 0, noFrame.Length);
                ctx.Response.Close();
                return;
            }

            ctx.Response.StatusCode = 200;
            ctx.Response.ContentType = "image/jpeg";
            ctx.Response.ContentLength64 = frame.Length;
            ctx.Response.AddHeader("Cache-Control", "no-cache, no-store, must-revalidate");
            ctx.Response.AddHeader("Pragma", "no-cache");
            ctx.Response.AddHeader("Expires", "0");
            ctx.Response.AddHeader("Access-Control-Allow-Origin", "*");
            ctx.Response.OutputStream.Write(frame, 0, frame.Length);
            ctx.Response.Close();
            return;
        }

        byte[] notFound = Encoding.UTF8.GetBytes("not found");
        ctx.Response.StatusCode = 404;
        ctx.Response.ContentType = "text/plain";
        ctx.Response.ContentLength64 = notFound.Length;
        ctx.Response.OutputStream.Write(notFound, 0, notFound.Length);
        ctx.Response.Close();
    }
}
