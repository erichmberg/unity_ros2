using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using Unity.Robotics.ROSTCPConnector.ROSGeometry;
using RosMessageTypes.Geometry;
using RosMessageTypes.Std;
using RosMessageTypes.BuiltinInterfaces;

/// <summary>
/// Publishes a target PoseStamped to ROS, but constrains the target in Unity world:
/// - only on negative X side
/// - max distance from beam in X (default 1.0m)
/// Optional randomization inside a bounded region around the beam.
/// </summary>
public class RailConstrainedTargetPublisher : MonoBehaviour
{
    [Header("ROS")]
    public string topicName = "/unity/grasp_target";
    public string frameId = "world";

    [Header("Target")]
    public Transform targetTransform;
    public bool createVisibleMarkerIfMissing = true;
    public float markerScale = 0.04f;

    [Header("Beam reference (Unity world)")]
    public Transform beamReference;
    public float beamX = 0.0f;

    [Header("Constraints")]
    public bool enforceNegativeX = true;
    public float maxDistanceFromBeamX = 1.0f;

    [Header("Random target region")]
    public bool enableRandomize = true;
    public Vector2 yRange = new Vector2(1.62f, 2.20f);
    public Vector2 zRange = new Vector2(0.10f, 0.55f);

    [Header("Keybinds")]
    public KeyCode publishKey = KeyCode.T;
    public KeyCode randomizeAndPublishKey = KeyCode.R;

    ROSConnection ros;

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.RegisterPublisher<PoseStampedMsg>(topicName);

        if (targetTransform == null)
            targetTransform = transform;

        if (targetTransform != null && createVisibleMarkerIfMissing)
        {
            var r = targetTransform.GetComponentInChildren<Renderer>();
            if (r == null)
            {
                var sphere = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                sphere.name = "TargetVisualMarker";
                sphere.transform.SetParent(targetTransform, false);
                sphere.transform.localPosition = Vector3.zero;
                sphere.transform.localRotation = Quaternion.identity;
                sphere.transform.localScale = Vector3.one * Mathf.Max(0.005f, markerScale);
            }
        }

        if (beamReference != null)
            beamX = beamReference.position.x;
    }

    void Update()
    {
        if (Input.GetKeyDown(publishKey))
            PublishNow();

        if (enableRandomize && Input.GetKeyDown(randomizeAndPublishKey))
            RandomizeAndPublish();
    }

    public void RandomizeAndPublish()
    {
        if (targetTransform == null)
            return;

        if (beamReference != null)
            beamX = beamReference.position.x;

        float minX = beamX - Mathf.Abs(maxDistanceFromBeamX);
        float maxX = enforceNegativeX ? Mathf.Min(beamX, 0f) : beamX + Mathf.Abs(maxDistanceFromBeamX);

        Vector3 p = targetTransform.position;
        p.x = Random.Range(minX, maxX);
        p.y = Random.Range(Mathf.Min(yRange.x, yRange.y), Mathf.Max(yRange.x, yRange.y));
        p.z = Random.Range(Mathf.Min(zRange.x, zRange.y), Mathf.Max(zRange.x, zRange.y));
        targetTransform.position = p;

        PublishNow();
    }

    public void PublishNow()
    {
        if (targetTransform == null)
        {
            Debug.LogWarning("RailConstrainedTargetPublisher: targetTransform is not set.");
            return;
        }

        if (beamReference != null)
            beamX = beamReference.position.x;

        // Enforce constraints in Unity world first
        Vector3 pUnity = targetTransform.position;
        float minX = beamX - Mathf.Abs(maxDistanceFromBeamX);
        float maxX = enforceNegativeX ? Mathf.Min(beamX, 0f) : beamX + Mathf.Abs(maxDistanceFromBeamX);
        pUnity.x = Mathf.Clamp(pUnity.x, minX, maxX);
        targetTransform.position = pUnity;

        // Convert to ROS FLU and publish
        var p = targetTransform.position.To<FLU>();
        var q = targetTransform.rotation.To<FLU>();

        var msg = new PoseStampedMsg
        {
            header = new HeaderMsg
            {
                stamp = new TimeMsg { sec = 0, nanosec = 0 },
                frame_id = frameId
            },
            pose = new PoseMsg
            {
                position = new PointMsg(p.x, p.y, p.z),
                orientation = new QuaternionMsg(q.x, q.y, q.z, q.w)
            }
        };

        ros.Publish(topicName, msg);
        Debug.Log($"RailConstrainedTargetPublisher: published {topicName} at Unity({pUnity.x:F3},{pUnity.y:F3},{pUnity.z:F3})");
    }
}
