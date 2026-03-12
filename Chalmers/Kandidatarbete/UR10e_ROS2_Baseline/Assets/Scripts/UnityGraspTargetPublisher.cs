using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using Unity.Robotics.ROSTCPConnector.ROSGeometry;
using RosMessageTypes.Geometry;
using RosMessageTypes.Std;
using RosMessageTypes.BuiltinInterfaces;

public class UnityGraspTargetPublisher : MonoBehaviour
{
    [Header("ROS")]
    public string topicName = "/unity/grasp_target";
    public string frameId = "world";

    [Header("Target")]
    public Transform targetTransform;
    public bool ensureVisibleTargetMarker = true;
    public float markerScale = 0.04f;

    [Header("Publishing")]
    public bool publishOnStart = false;
    public bool publishContinuously = false;
    public float publishRateHz = 2.0f;
    public KeyCode publishKey = KeyCode.T;

    [Header("ROS-frame safety constraints (after Unity->FLU conversion)")]
    public bool enforceRosConstraints = true;
    public float rosMinX = 1.63f;   // rail height ~1.60 + clearance
    public float rosMinZ = 0.10f;   // keep in front-side band
    public float rosRailCenterY = 0.0f;
    public float rosMaxDistanceFromRailY = 0.75f;

    ROSConnection ros;
    float nextPublishTime;

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.RegisterPublisher<PoseStampedMsg>(topicName);
        Debug.Log($"UnityGraspTargetPublisher ready on topic: {topicName}");

        if (targetTransform != null && ensureVisibleTargetMarker)
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
                Debug.Log("UnityGraspTargetPublisher: created fallback visible marker sphere.");
            }
        }

        if (publishOnStart)
            PublishNow();
    }

    void Update()
    {
        if (Input.GetKeyDown(publishKey))
            PublishNow();

        if (publishContinuously && Time.time >= nextPublishTime)
        {
            PublishNow();
            nextPublishTime = Time.time + 1.0f / Mathf.Max(0.1f, publishRateHz);
        }
    }

    public void PublishNow()
    {
        if (targetTransform == null)
        {
            Debug.LogWarning("UnityGraspTargetPublisher: targetTransform is not set.");
            return;
        }

        var tools = targetTransform.GetComponent<TargetWorkspaceTools>();
        if (tools == null)
            tools = targetTransform.GetComponentInParent<TargetWorkspaceTools>();
        if (tools != null)
            tools.ClampTargetToRailDistance();

        var p = targetTransform.position.To<FLU>();
        var q = targetTransform.rotation.To<FLU>();

        // Apply limits in ROS/FLU frame so axis mapping is always correct.
        if (enforceRosConstraints)
        {
            p.x = Mathf.Max(p.x, rosMinX);
            p.z = Mathf.Max(p.z, rosMinZ);
            p.y = Mathf.Clamp(p.y, rosRailCenterY - rosMaxDistanceFromRailY, rosRailCenterY + rosMaxDistanceFromRailY);
        }

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
        Debug.Log($"Published grasp target to {topicName}: ({p.x:F3}, {p.y:F3}, {p.z:F3}) frame={frameId}");
    }
}
