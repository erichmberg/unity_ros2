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

    [Header("Rail Joint Tuning")]
    public string railJointName = "rail_joint";
    public float railMaxMetersPerSecond = 0.35f;
    public float railStiffness = 40000f;
    public float railDamping = 6000f;
    public float railForceLimit = 100000f;

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
        if (points == null || points.Length == 0 || jointNames == null || tPoints == null) return;

        // Handle single-point trajectories directly (common for quick tests).
        if (points.Length == 1 || tPoints.Length == 1)
        {
            ApplyPositions(points[0].positions);
            return;
        }

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

        // guard if we ended up on last index before interpolation
        if (k >= last)
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
            bool isRail = string.Equals(jName, railJointName, StringComparison.OrdinalIgnoreCase);

            // For revolute joints ROS values are radians; for prismatic values are meters.
            float desired = isPrismatic
                ? (float)positions[i]
                : (float)(positions[i] * Mathf.Rad2Deg);

            var drive = joint.xDrive;

            // Ensure usable gains. Rail needs much higher force to carry whole arm mass.
            if (isRail)
            {
                drive.stiffness = Mathf.Max(drive.stiffness, railStiffness);
                drive.damping = Mathf.Max(drive.damping, railDamping);
                drive.forceLimit = Mathf.Max(drive.forceLimit, railForceLimit);
            }
            else
            {
                if (drive.stiffness <= 0f) drive.stiffness = 800f;
                if (drive.damping <= 0f) drive.damping = 200f;
                if (drive.forceLimit <= 0f) drive.forceLimit = 300f;
            }

            // Speed-limit commanded target (deg/s for revolute, m/s for prismatic).
            float current = cmdTarget.TryGetValue(jName, out var v) ? v : drive.target;
            float speed = isPrismatic
                ? (isRail ? railMaxMetersPerSecond : (isFinger ? fingerMaxMetersPerSecond : maxMetersPerSecond))
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
        Debug.Log($"JointTrajectoryToUr10e: mapped {jointMap.Count} joints");
    }

    void TryAdd(Component urdfJoint)
    {
        string name = GetJointNameReflection(urdfJoint);
        if (string.IsNullOrEmpty(name)) return;

        var ab = urdfJoint.GetComponent<ArticulationBody>();
        if (ab == null) return;

        if (!jointMap.ContainsKey(name))
        {
            // Keep imported/default pose at startup; do not force all joints to hardcoded targets.
            // This prevents slow drift right after pressing Play when no trajectory has been commanded yet.
            jointMap.Add(name, ab);
            cmdTarget[name] = ab.xDrive.target;
        }
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
