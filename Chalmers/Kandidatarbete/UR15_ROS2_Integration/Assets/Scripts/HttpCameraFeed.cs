using System.Collections;
using UnityEngine;
using UnityEngine.Networking;
using UnityEngine.UI;

/// <summary>
/// Polls a JPEG endpoint (e.g. http://127.0.0.1:8080/frame.jpg) and renders it in Unity.
/// Attach to any GameObject, then assign either targetRenderer (material mainTexture)
/// or targetRawImage (UI) in the inspector.
/// </summary>
public class HttpCameraFeed : MonoBehaviour
{
    [Header("HTTP Camera Source")]
    public string imageUrl = "http://192.168.50.165:18081/frame.jpg";
    [Range(1f, 60f)] public float fps = 15f;
    public float requestTimeoutSeconds = 2f;

    [Header("Display Target (pick one or both)")]
    public Renderer targetRenderer;
    public RawImage targetRawImage;

    Texture2D _latestTexture;
    bool _running;

    void OnEnable()
    {
        _running = true;
        StartCoroutine(PollLoop());
    }

    void OnDisable()
    {
        _running = false;
        if (_latestTexture != null)
        {
            Destroy(_latestTexture);
            _latestTexture = null;
        }
    }

    IEnumerator PollLoop()
    {
        var wait = new WaitForSeconds(1f / Mathf.Max(1f, fps));

        while (_running)
        {
            using (UnityWebRequest req = UnityWebRequestTexture.GetTexture(imageUrl, nonReadable: false))
            {
                req.timeout = Mathf.CeilToInt(requestTimeoutSeconds);
                yield return req.SendWebRequest();

                if (req.result == UnityWebRequest.Result.Success)
                {
                    Texture2D tex = DownloadHandlerTexture.GetContent(req);
                    ApplyTexture(tex);
                }
                else
                {
                    Debug.LogWarning($"HttpCameraFeed request failed: {req.error}");
                }
            }

            yield return wait;
        }
    }

    void ApplyTexture(Texture2D newTexture)
    {
        if (newTexture == null) return;

        if (_latestTexture != null && _latestTexture != newTexture)
            Destroy(_latestTexture);

        _latestTexture = newTexture;

        if (targetRenderer != null && targetRenderer.material != null)
            targetRenderer.material.mainTexture = _latestTexture;

        if (targetRawImage != null)
            targetRawImage.texture = _latestTexture;
    }
}
