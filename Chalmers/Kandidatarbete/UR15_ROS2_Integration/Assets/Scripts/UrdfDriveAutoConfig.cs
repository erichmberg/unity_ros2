using System;
using System.Reflection;
using UnityEngine;

/// <summary>
/// Applies default articulation-drive settings to URDF joints automatically at runtime.
/// Targets all ArticulationBody joints in scene (revolute/prismatic/spherical where relevant).
/// </summary>
public class UrdfDriveAutoConfig : MonoBehaviour
{
    [Header("Drive Defaults")]
    public float lowerLimitDeg = -180f;
    public float upperLimitDeg = 180f;
    public float stiffness = 800f;
    public float damping = 200f;
    public float forceLimit = 300f;
    public float target = 0f;
    public float targetVelocity = 0f;

    [Header("Safety / Stability")]
    public bool excludeFingerJointsFromGlobalDrive = true;
    public bool disableGravityOnFingerJoints = true;
    public float fingerLinearDamping = 8f;
    public float fingerAngularDamping = 8f;

    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void AutoCreate()
    {
        if (FindAnyObjectByType<UrdfDriveAutoConfig>() != null)
            return;

        var go = new GameObject("UrdfDriveAutoConfig_Auto");
        DontDestroyOnLoad(go);
        go.AddComponent<UrdfDriveAutoConfig>();
    }

    void Start()
    {
        ApplyToAll();
    }

    public void ApplyToAll()
    {
        var allBodies = FindObjectsByType<ArticulationBody>(FindObjectsSortMode.None);
        int updated = 0;

        foreach (var body in allBodies)
        {
            if (body == null) continue;

            string n = body.name.ToLowerInvariant();
            bool isFinger = n.Contains("finger") || n.Contains("gripper");

            // Stabilize fingers so they don't "fall off" due to aggressive global config.
            if (isFinger)
            {
                if (disableGravityOnFingerJoints)
                    body.useGravity = false;

                body.linearDamping = Mathf.Max(body.linearDamping, fingerLinearDamping);
                body.angularDamping = Mathf.Max(body.angularDamping, fingerAngularDamping);
            }

            // Apply requested drive mode if this Unity version exposes it.
            TrySetDriveTypeForce(body);

            // Optional: keep finger drives managed by dedicated gripper script.
            if (isFinger && excludeFingerJointsFromGlobalDrive)
                continue;

            if (body.jointType == ArticulationJointType.RevoluteJoint || body.jointType == ArticulationJointType.PrismaticJoint)
            {
                var d = body.xDrive;
                d.lowerLimit = lowerLimitDeg;
                d.upperLimit = upperLimitDeg;
                d.stiffness = stiffness;
                d.damping = damping;
                d.forceLimit = forceLimit;
                d.target = target;
                d.targetVelocity = targetVelocity;
                body.xDrive = d;
                updated++;
            }
            else if (body.jointType == ArticulationJointType.SphericalJoint)
            {
                var dx = body.xDrive;
                dx.lowerLimit = lowerLimitDeg;
                dx.upperLimit = upperLimitDeg;
                dx.stiffness = stiffness;
                dx.damping = damping;
                dx.forceLimit = forceLimit;
                dx.target = target;
                dx.targetVelocity = targetVelocity;
                body.xDrive = dx;

                var dy = body.yDrive;
                dy.lowerLimit = lowerLimitDeg;
                dy.upperLimit = upperLimitDeg;
                dy.stiffness = stiffness;
                dy.damping = damping;
                dy.forceLimit = forceLimit;
                dy.target = target;
                dy.targetVelocity = targetVelocity;
                body.yDrive = dy;

                var dz = body.zDrive;
                dz.lowerLimit = lowerLimitDeg;
                dz.upperLimit = upperLimitDeg;
                dz.stiffness = stiffness;
                dz.damping = damping;
                dz.forceLimit = forceLimit;
                dz.target = target;
                dz.targetVelocity = targetVelocity;
                body.zDrive = dz;
                updated++;
            }
        }

        Debug.Log($"UrdfDriveAutoConfig: applied drive defaults to {updated} joints.");
    }

    void TrySetDriveTypeForce(ArticulationBody body)
    {
        try
        {
            var prop = typeof(ArticulationBody).GetProperty("driveType", BindingFlags.Public | BindingFlags.Instance);
            if (prop == null || !prop.CanWrite || !prop.PropertyType.IsEnum) return;

            foreach (var name in Enum.GetNames(prop.PropertyType))
            {
                if (string.Equals(name, "Force", StringComparison.OrdinalIgnoreCase))
                {
                    var enumValue = Enum.Parse(prop.PropertyType, name);
                    prop.SetValue(body, enumValue);
                    return;
                }
            }
        }
        catch
        {
            // No-op on Unity versions without this property.
        }
    }
}
