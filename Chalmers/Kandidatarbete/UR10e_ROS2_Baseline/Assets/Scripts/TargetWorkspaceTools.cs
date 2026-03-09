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

    [Header("Simple reachability")]
    public float minReachMeters = 0.18f;
    public float maxReachMeters = 1.05f;

    [Header("Colors")]
    public Color reachableColor = new Color(0.10f, 0.85f, 0.25f, 1f);
    public Color unreachableColor = new Color(0.90f, 0.15f, 0.15f, 1f);

    [Header("Keybinds")]
    public KeyCode randomizeKey = KeyCode.R;
    public KeyCode randomizeAndPublishKey = KeyCode.T;

    void Start()
    {
        if (targetTransform == null)
            targetTransform = transform;

        if (targetRenderer == null && targetTransform != null)
            targetRenderer = targetTransform.GetComponentInChildren<Renderer>();

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

        var p = new Vector3(
            Random.Range(minBounds.x, maxBounds.x),
            Random.Range(minBounds.y, maxBounds.y),
            Random.Range(minBounds.z, maxBounds.z)
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

        // Extra floor sanity guard
        if (targetTransform.position.z < minBounds.z)
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
}
