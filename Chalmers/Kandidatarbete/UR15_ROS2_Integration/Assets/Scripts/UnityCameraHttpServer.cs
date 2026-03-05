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
///   GET /pose.json    -> current end-effector XYZ
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

    [Header("Pose Overlay")]
    public bool overlayPoseText = true;
    public string endEffectorNameContains = "wrist_3";

    private static byte[] s_latestJpeg;
    private static readonly object s_frameLock = new object();
    private static int s_streamFps = 10;
    private static Vector3 s_endEffectorWorldPos;

    private Camera _targetCamera;
    private Transform _endEffector;
    private Transform _overlayTransform;
    private TextMesh _overlayText;
    private RenderTexture _rt;
    private Texture2D _readTex;
    private int _appliedWidth;
    private int _appliedHeight;
    private int _appliedFps;

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

        _endEffector = FindEndEffectorTransform();
        if (overlayPoseText)
            CreateOverlayText();

        StartHttpServer();
        ApplyCaptureSettings(force: true);

        Debug.Log($"UnityCameraHttpServer running: http://0.0.0.0:{port}/frame.jpg");
    }

    void OnDestroy()
    {
        StopHttpServer();
        CancelInvoke(nameof(CaptureFrame));

        if (_rt != null) _rt.Release();
        if (_readTex != null) Destroy(_readTex);
    }

    void Update()
    {
        ApplyCaptureSettings(force: false);

        if (_endEffector != null)
            s_endEffectorWorldPos = _endEffector.position;

        if (overlayPoseText && _overlayText != null && _targetCamera != null)
        {
            Vector3 p = s_endEffectorWorldPos;
            _overlayText.text = $"X: {p.x:F3}  Y: {p.y:F3}  Z: {p.z:F3}";

            // Place overlay near top-left of camera view.
            Vector3 world = _targetCamera.ViewportToWorldPoint(new Vector3(0.05f, 0.95f, 1.0f));
            _overlayTransform.position = world;
            _overlayTransform.rotation = _targetCamera.transform.rotation;
        }
    }

    Transform FindEndEffectorTransform()
    {
        string needle = (endEffectorNameContains ?? string.Empty).ToLowerInvariant();
        if (string.IsNullOrWhiteSpace(needle))
            needle = "wrist_3";

        foreach (Transform t in FindObjectsByType<Transform>(FindObjectsSortMode.None))
        {
            if (t.name.ToLowerInvariant().Contains(needle))
            {
                Debug.Log($"UnityCameraHttpServer: End-effector target='{t.name}'");
                return t;
            }
        }

        Debug.LogWarning($"UnityCameraHttpServer: Could not find end effector containing '{needle}'. Overlay will show last known values.");
        return null;
    }

    void CreateOverlayText()
    {
        var go = new GameObject("UnityPoseOverlayText");
        go.transform.SetParent(_targetCamera.transform, false);
        _overlayTransform = go.transform;

        _overlayText = go.AddComponent<TextMesh>();
        _overlayText.fontSize = 40;
        _overlayText.characterSize = 0.02f;
        _overlayText.anchor = TextAnchor.UpperLeft;
        _overlayText.alignment = TextAlignment.Left;
        _overlayText.color = Color.white;
        _overlayText.text = "X: 0.000  Y: 0.000  Z: 0.000";

        var mr = go.GetComponent<MeshRenderer>();
        if (mr != null)
        {
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            mr.receiveShadows = false;
        }
    }

    void ApplyCaptureSettings(bool force)
    {
        int w = Mathf.Max(64, width);
        int h = Mathf.Max(64, height);
        int f = Mathf.Max(1, fps);

        bool sizeChanged = force || w != _appliedWidth || h != _appliedHeight;
        bool fpsChanged = force || f != _appliedFps;

        if (sizeChanged)
        {
            if (_rt != null)
            {
                _rt.Release();
                Destroy(_rt);
            }
            if (_readTex != null)
                Destroy(_readTex);

            _rt = new RenderTexture(w, h, 16, RenderTextureFormat.ARGB32);
            _readTex = new Texture2D(w, h, TextureFormat.RGB24, false);

            _appliedWidth = w;
            _appliedHeight = h;
            Debug.Log($"UnityCameraHttpServer: applied stream resolution {w}x{h}");
        }

        if (fpsChanged)
        {
            _appliedFps = f;
            s_streamFps = f;
            CancelInvoke(nameof(CaptureFrame));
            InvokeRepeating(nameof(CaptureFrame), 0.02f, 1f / _appliedFps);
            Debug.Log($"UnityCameraHttpServer: applied stream fps {_appliedFps}");
        }
    }

    void CaptureFrame()
    {
        if (_targetCamera == null) return;
        if (_rt == null || _readTex == null) return;

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

        if (path.Equals("/pose.json", StringComparison.OrdinalIgnoreCase))
        {
            Vector3 p = s_endEffectorWorldPos;
            string json = $"{{\"x\":{p.x:F6},\"y\":{p.y:F6},\"z\":{p.z:F6}}}";
            byte[] payload = Encoding.UTF8.GetBytes(json);
            ctx.Response.StatusCode = 200;
            ctx.Response.ContentType = "application/json";
            ctx.Response.ContentLength64 = payload.Length;
            ctx.Response.AddHeader("Access-Control-Allow-Origin", "*");
            ctx.Response.OutputStream.Write(payload, 0, payload.Length);
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

                    Thread.Sleep(Mathf.Max(1, 1000 / Mathf.Max(1, s_streamFps))); // stream pacing tied to configured fps
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
