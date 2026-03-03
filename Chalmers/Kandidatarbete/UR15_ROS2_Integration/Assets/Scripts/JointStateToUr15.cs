using System;
using System.Collections.Generic;
using System.Reflection;
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Sensor;
using Unity.Robotics.UrdfImporter;

public class JointStateToUr15 : MonoBehaviour
{
    [Header("ROS")]
    public string topicName = "/unity/ur15_joint_command";

    [Header("Drive axis to command")]
    public DriveAxis driveAxis = DriveAxis.X;
    public enum DriveAxis { X, Y, Z }

    readonly Dictionary<string, ArticulationBody> jointMap = new();

    void Start()
    {
        BuildJointMapFromUrdf();
        ROSConnection.GetOrCreateInstance().Subscribe<JointStateMsg>(topicName, OnJointState);
    }

    void BuildJointMapFromUrdf()
    {
        jointMap.Clear();

        foreach (var uj in GetComponentsInChildren<UrdfJointRevolute>(true))
            TryAdd(uj);

        foreach (var uj in GetComponentsInChildren<UrdfJointPrismatic>(true))
            TryAdd(uj);

        Debug.Log($"JointStateToUr15: mapped {jointMap.Count} joints");
        foreach (var kv in jointMap)
            Debug.Log($"ROS '{kv.Key}' -> '{kv.Value.gameObject.name}'");
    }

    void TryAdd(Component urdfJoint)
    {
        string jointName = GetJointNameReflection(urdfJoint);
        if (string.IsNullOrEmpty(jointName))
            return;

        var ab = urdfJoint.GetComponent<ArticulationBody>();
        if (ab == null)
            return;

        if (!jointMap.ContainsKey(jointName))
            jointMap.Add(jointName, ab);
    }

    static string GetJointNameReflection(Component urdfJoint)
    {
        // URDF Importer versions differ; commonly a private/public field named "jointName"
        // or a property named "jointName"/"JointName".
        var t = urdfJoint.GetType();

        const BindingFlags flags = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;

        var prop = t.GetProperty("JointName", flags) ?? t.GetProperty("jointName", flags);
        if (prop != null && prop.PropertyType == typeof(string))
            return prop.GetValue(urdfJoint) as string;

        var field = t.GetField("jointName", flags) ?? t.GetField("JointName", flags);
        if (field != null && field.FieldType == typeof(string))
            return field.GetValue(urdfJoint) as string;

        return null;
    }

    void OnJointState(JointStateMsg msg)
    {
        if (msg?.name == null || msg.position == null) return;

        int n = Math.Min(msg.name.Length, msg.position.Length);
        for (int i = 0; i < n; i++)
        {
            if (!jointMap.TryGetValue(msg.name[i], out var joint))
                continue;

            float targetDeg = (float)(msg.position[i] * Mathf.Rad2Deg);

            ArticulationDrive drive = driveAxis switch
            {
                DriveAxis.Y => joint.yDrive,
                DriveAxis.Z => joint.zDrive,
                _ => joint.xDrive
            };

            // Ensure non-zero gains so it moves
            if (drive.stiffness <= 0f) drive.stiffness = 10000f;
            if (drive.damping <= 0f) drive.damping = 500f;
            if (drive.forceLimit <= 0f) drive.forceLimit = 1000f;

            drive.target = targetDeg;

            switch (driveAxis)
            {
                case DriveAxis.Y: joint.yDrive = drive; break;
                case DriveAxis.Z: joint.zDrive = drive; break;
                default: joint.xDrive = drive; break;
            }
        }
    }
}
