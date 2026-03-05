using System;
using System.Collections.Generic;
using System.Reflection;
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Trajectory;
using Unity.Robotics.UrdfImporter;

public class JointTrajectoryToUr10e : MonoBehaviour
{
    public string topicName = "/unity/ur10e_joint_trajectory";
    public float maxDegreesPerSecond = 120f;
    public float fingerMaxDegreesPerSecond = 220f;
    public float maxMetersPerSecond = 0.20f;
    public float fingerMaxMetersPerSecond = 0.06f;

    readonly Dictionary<string, ArticulationBody> jointMap = new();
    readonly Dictionary<string, float> cmdTarget = new();

    // Active trajectory
    JointTrajectoryPointMsg[] points;
    double[] tPoints;
    string[] jointNames;
    double t0;

    void Start()
    {
        BuildJointMapFromUrdf();
        var ros = ROSConnection.GetOrCreateInstance();
        ros.Subscribe<JointTrajectoryMsg>(topicName, OnTrajectory);
        Debug.Log($"JointTrajectoryToUr10e subscribed to: {topicName}");
    }

    void FixedUpdate()
    {
        if (points == null || points.Length == 0 || jointNames == null) return;

        double t = Time.timeAsDouble - t0;

        // find segment
        int last = points.Length - 1;
        int k = 0;
        while (k < last && t > tPoints[k + 1]) k++;

        // clamp to final point
        if (t >= tPoints[last])
        {
            ApplyPositions(points[last].positions);
            return;
        }

        // interpolate between k and k+1
        double tA = tPoints[k];
        double tB = tPoints[k + 1];
        double u = (tB <= tA) ? 1.0 : (t - tA) / (tB - tA);

        var a = points[k].positions;
        var b = points[k + 1].positions;

        if (a == null || b == null) return;

        double[] interp = new double[Math.Min(a.Length, b.Length)];
        for (int i = 0; i < interp.Length; i++)
            interp[i] = a[i] + (b[i] - a[i]) * u;

        ApplyPositions(interp);
    }

    void OnTrajectory(JointTrajectoryMsg msg)
    {
        jointNames = msg.joint_names;
        points = msg.points;

        if (jointNames == null || points == null || points.Length == 0)
            return;

        // Precompute times (seconds) for each point
        tPoints = new double[points.Length];
        for (int i = 0; i < points.Length; i++)
        {
            var d = points[i].time_from_start;
            tPoints[i] = d.sec + d.nanosec * 1e-9;
        }

        t0 = Time.timeAsDouble;
    }

    void ApplyPositions(double[] positions)
    {
        int n = Math.Min(jointNames.Length, positions.Length);
        for (int i = 0; i < n; i++)
        {
            string jName = jointNames[i];
            if (!jointMap.TryGetValue(jName, out var joint))
                continue;

            bool isFinger = jName.IndexOf("finger", StringComparison.OrdinalIgnoreCase) >= 0;
            bool isPrismatic = joint.jointType == ArticulationJointType.PrismaticJoint;

            // For revolute joints ROS values are radians; for prismatic values are meters.
            float desired = isPrismatic
                ? (float)positions[i]
                : (float)(positions[i] * Mathf.Rad2Deg);

            var drive = joint.xDrive;

            // Ensure usable gains
            if (isFinger)
            {
                if (drive.stiffness <= 0f) drive.stiffness = 8000f;
                if (drive.damping <= 0f) drive.damping = 300f;
                if (drive.forceLimit <= 0f) drive.forceLimit = 3000f;
            }
            else
            {
                if (drive.stiffness <= 0f) drive.stiffness = 1500f;
                if (drive.damping <= 0f) drive.damping = 400f;
                if (drive.forceLimit <= 0f) drive.forceLimit = 1000f;
            }

            // Speed-limit commanded target (deg/s for revolute, m/s for prismatic).
            float current = cmdTarget.TryGetValue(jName, out var v) ? v : drive.target;
            float speed = isPrismatic
                ? (isFinger ? fingerMaxMetersPerSecond : maxMetersPerSecond)
                : (isFinger ? fingerMaxDegreesPerSecond : maxDegreesPerSecond);
            float maxStep = speed * Time.fixedDeltaTime;
            float next = Mathf.MoveTowards(current, desired, maxStep);

            drive.target = next;
            joint.xDrive = drive;

            cmdTarget[jName] = next;
        }
    }

    void BuildJointMapFromUrdf()
    {
        jointMap.Clear();
        foreach (var uj in GetComponentsInChildren<UrdfJointRevolute>(true))
            TryAdd(uj);
        foreach (var uj in GetComponentsInChildren<UrdfJointPrismatic>(true))
            TryAdd(uj);
        Debug.Log($"JointTrajectoryToUr15: mapped {jointMap.Count} joints");
    }

    void TryAdd(Component urdfJoint)
    {
        string name = GetJointNameReflection(urdfJoint);
        if (string.IsNullOrEmpty(name)) return;

        var ab = urdfJoint.GetComponent<ArticulationBody>();
        if (ab == null) return;

        if (!jointMap.ContainsKey(name))
            jointMap.Add(name, ab);
    }

    static string GetJointNameReflection(Component urdfJoint)
    {
        var t = urdfJoint.GetType();
        const BindingFlags flags = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;

        var prop = t.GetProperty("jointName", flags) ?? t.GetProperty("JointName", flags);
        if (prop != null && prop.PropertyType == typeof(string))
            return prop.GetValue(urdfJoint) as string;

        var field = t.GetField("jointName", flags) ?? t.GetField("JointName", flags);
        if (field != null && field.FieldType == typeof(string))
            return field.GetValue(urdfJoint) as string;

        return null;
    }
}
