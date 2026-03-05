using UnityEngine;

/// <summary>
/// Safety script: anchors all articulation roots at runtime so imported robots
/// don't tip over due to scene-level gravity/physics settings.
/// </summary>
public class AutoAnchorArticulationRoots : MonoBehaviour
{
    [Header("Anchor Settings")]
    public bool anchorAllRoots = true;
    public bool disableGravityOnRoot = true;

    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void AutoCreate()
    {
        if (FindAnyObjectByType<AutoAnchorArticulationRoots>() != null)
            return;

        var go = new GameObject("AutoAnchorArticulationRoots_Auto");
        DontDestroyOnLoad(go);
        go.AddComponent<AutoAnchorArticulationRoots>();
    }

    void Start()
    {
        Apply();
    }

    public void Apply()
    {
        var all = FindObjectsByType<ArticulationBody>(FindObjectsSortMode.None);
        int anchored = 0;

        foreach (var ab in all)
        {
            if (ab == null) continue;
            if (!ab.isRoot) continue;
            if (!anchorAllRoots) continue;

            ab.immovable = true;
            if (disableGravityOnRoot)
                ab.useGravity = false;

            // extra stability
            ab.linearDamping = Mathf.Max(ab.linearDamping, 5f);
            ab.angularDamping = Mathf.Max(ab.angularDamping, 5f);

            anchored++;
        }

        Debug.Log($"AutoAnchorArticulationRoots: anchored {anchored} articulation root(s).");
    }
}
