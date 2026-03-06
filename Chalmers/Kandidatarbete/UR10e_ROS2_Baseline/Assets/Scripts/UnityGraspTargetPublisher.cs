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

    [Header("Publishing")]
    public bool publishOnStart = false;
    public bool publishContinuously = false;
    public float publishRateHz = 2.0f;
    public KeyCode publishKey = KeyCode.G;

    ROSConnection ros;
    float nextPublishTime;

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.RegisterPublisher<PoseStampedMsg>(topicName);
        Debug.Log($"UnityGraspTargetPublisher ready on topic: {topicName}");

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
        Debug.Log($"Published grasp target to {topicName}: ({p.x:F3}, {p.y:F3}, {p.z:F3}) frame={frameId}");
    }
}
