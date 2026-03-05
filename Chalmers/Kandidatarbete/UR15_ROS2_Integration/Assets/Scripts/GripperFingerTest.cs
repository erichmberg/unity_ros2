using UnityEngine;

/// <summary>
/// Quick keyboard test for two-finger gripper articulation drives.
/// Keys:
///   O = open
///   C = close
///   Space = toggle
///   [ / ] = fine adjust target
/// </summary>
public class GripperFingerTest : MonoBehaviour
{
    [Header("Assign in Inspector")]
    public ArticulationBody leftFinger;
    public ArticulationBody rightFinger;

    [Header("Targets")]
    public float openTarget = 0.0f;
    public float closeTarget = 0.65f;
    public float step = 0.02f;

    [Header("Direction")]
    public bool invertRightFinger = false;

    private float _currentTarget;
    private bool _isClosed;

    void Start()
    {
        _currentTarget = openTarget;
        ApplyTarget(_currentTarget);
    }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.O))
        {
            _isClosed = false;
            _currentTarget = openTarget;
            ApplyTarget(_currentTarget);
        }

        if (Input.GetKeyDown(KeyCode.C))
        {
            _isClosed = true;
            _currentTarget = closeTarget;
            ApplyTarget(_currentTarget);
        }

        if (Input.GetKeyDown(KeyCode.Space))
        {
            _isClosed = !_isClosed;
            _currentTarget = _isClosed ? closeTarget : openTarget;
            ApplyTarget(_currentTarget);
        }

        if (Input.GetKeyDown(KeyCode.LeftBracket))
        {
            _currentTarget -= step;
            ApplyTarget(_currentTarget);
        }

        if (Input.GetKeyDown(KeyCode.RightBracket))
        {
            _currentTarget += step;
            ApplyTarget(_currentTarget);
        }
    }

    void ApplyTarget(float t)
    {
        if (leftFinger != null)
        {
            var d = leftFinger.xDrive;
            d.target = t;
            leftFinger.xDrive = d;
        }

        if (rightFinger != null)
        {
            var d = rightFinger.xDrive;
            d.target = invertRightFinger ? -t : t;
            rightFinger.xDrive = d;
        }

        Debug.Log($"GripperFingerTest target={t:F3}");
    }
}
