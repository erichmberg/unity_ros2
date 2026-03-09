using UnityEngine;

/// <summary>
/// Utility for demo targets:
/// - Randomize target transform inside a safe workspace box
/// - Color target renderer based on simple reachability check
/// - Optional one-click randomize+publish via UnityGraspTargetPublisher
/// </summary>
public class TargetWorkspaceTools : MonoBehaviour
{
    [Header("References")]
    public Transform targetTransform;
    public Transform robotBaseTransform;
    public UnityGraspTargetPublisher publisher;
    public Renderer targetRenderer;

    [Header("Workspace bounds (world)")]
    public Vector3 minBounds = new Vector3(0.20f, -0.35f, 0.20f);
    public Vector3 maxBounds = new Vector3(0.65f, 0.35f, 0.55f);

    public enum UpAxis { Y, Z }

    [Header("Floor safety")]
    public UpAxis upAxis = UpAxis.Y;
    public float floorLevel = 0.0f;
    public float minClearanceAboveFloor = 0.06f;

    [Header("Simple reachability")]
    public float minReachMeters = 0.18f;
    public float maxReachMeters = 1.05f;

    [Header("Colors")]
    public Color reachableColor = new Color(0.10f, 0.85f, 0.25f, 1f);
    public Color unreachableColor = new Color(0.90f, 0.15f, 0.15f, 1f);

    [Header("Visibility")]
    public bool autoCreateVisibleMarkerIfMissing = true;
    public float markerScale = 0.04f;

    [Header("Keybinds")]
    public KeyCode randomizeKey = KeyCode.R;
    public KeyCode randomizeAndPublishKey = KeyCode.T;

    void Start()
    {
        if (targetTransform == null)
            targetTransform = transform;

        if (targetRenderer == null && targetTransform != null)
            targetRenderer = targetTransform.GetComponentInChildren<Renderer>();

        if (targetRenderer == null && autoCreateVisibleMarkerIfMissing && targetTransform != null)
        {
            var sphere = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            sphere.name = "TargetVisualMarker";
            sphere.transform.SetParent(targetTransform, false);
            sphere.transform.localPosition = Vector3.zero;
            sphere.transform.localRotation = Quaternion.identity;
            sphere.transform.localScale = Vector3.one * Mathf.Max(0.005f, markerScale);
            targetRenderer = sphere.GetComponent<Renderer>();
            Debug.Log("TargetWorkspaceTools: created fallback visible marker sphere.");
        }

        if (publisher == null)
            publisher = FindObjectOfType<UnityGraspTargetPublisher>();

        UpdateReachabilityColor();
    }

    void Update()
    {
        if (Input.GetKeyDown(randomizeKey))
            RandomizeTargetInBounds();

        if (Input.GetKeyDown(randomizeAndPublishKey))
            RandomizeAndPublish();
    }

    public void RandomizeTargetInBounds()
    {
        if (targetTransform == null)
            return;

        float safeMinUp = Mathf.Max(
            upAxis == UpAxis.Y ? minBounds.y : minBounds.z,
            floorLevel + minClearanceAboveFloor
        );

        var p = new Vector3(
            Random.Range(minBounds.x, maxBounds.x),
            upAxis == UpAxis.Y ? Random.Range(safeMinUp, maxBounds.y) : Random.Range(minBounds.y, maxBounds.y),
            upAxis == UpAxis.Z ? Random.Range(safeMinUp, maxBounds.z) : Random.Range(minBounds.z, maxBounds.z)
        );

        targetTransform.position = p;
        UpdateReachabilityColor();
    }

    public void PublishTarget()
    {
        if (publisher == null)
        {
            Debug.LogWarning("TargetWorkspaceTools: publisher is missing.");
            return;
        }

        // Ensure publisher uses this target
        if (publisher.targetTransform == null)
            publisher.targetTransform = targetTransform;

        publisher.PublishNow();
    }

    public void RandomizeAndPublish()
    {
        RandomizeTargetInBounds();
        PublishTarget();
    }

    public bool IsReachableSimple()
    {
        if (targetTransform == null || robotBaseTransform == null)
            return true;

        float d = Vector3.Distance(targetTransform.position, robotBaseTransform.position);
        if (d < minReachMeters || d > maxReachMeters)
            return false;

        // Extra floor sanity guard (based on selected up axis)
        float up = upAxis == UpAxis.Y ? targetTransform.position.y : targetTransform.position.z;
        float minUp = Mathf.Max(upAxis == UpAxis.Y ? minBounds.y : minBounds.z, floorLevel + minClearanceAboveFloor);
        if (up < minUp)
            return false;

        return true;
    }

    public void UpdateReachabilityColor()
    {
        if (targetRenderer == null)
            return;

        bool ok = IsReachableSimple();
        if (targetRenderer.material != null)
            targetRenderer.material.color = ok ? reachableColor : unreachableColor;
    }

    void OnDrawGizmosSelected()
    {
        // Workspace box
        Gizmos.color = new Color(0.2f, 0.8f, 1f, 0.25f);
        Vector3 center = (minBounds + maxBounds) * 0.5f;
        Vector3 size = maxBounds - minBounds;
        Gizmos.DrawCube(center, size);

        Gizmos.color = new Color(0.2f, 0.8f, 1f, 0.9f);
        Gizmos.DrawWireCube(center, size);

        // Floor plane outline at configured level
        Gizmos.color = Color.yellow;
        if (upAxis == UpAxis.Y)
        {
            Vector3 a = new Vector3(minBounds.x, floorLevel, minBounds.z);
            Vector3 b = new Vector3(maxBounds.x, floorLevel, minBounds.z);
            Vector3 c = new Vector3(maxBounds.x, floorLevel, maxBounds.z);
            Vector3 d = new Vector3(minBounds.x, floorLevel, maxBounds.z);
            Gizmos.DrawLine(a, b);
            Gizmos.DrawLine(b, c);
            Gizmos.DrawLine(c, d);
            Gizmos.DrawLine(d, a);
        }
        else
        {
            Vector3 a = new Vector3(minBounds.x, minBounds.y, floorLevel);
            Vector3 b = new Vector3(maxBounds.x, minBounds.y, floorLevel);
            Vector3 c = new Vector3(maxBounds.x, maxBounds.y, floorLevel);
            Vector3 d = new Vector3(minBounds.x, maxBounds.y, floorLevel);
            Gizmos.DrawLine(a, b);
            Gizmos.DrawLine(b, c);
            Gizmos.DrawLine(c, d);
            Gizmos.DrawLine(d, a);
        }
    }
}
