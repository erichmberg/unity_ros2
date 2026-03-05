# NEXT STEPS — UR10e + MoveIt2 + CHOMP + RGB-D Bin Picking

## Current Status (Done)
- UR10e imported in Unity and controllable from ROS2 trajectory topic.
- Gripper integrated and moving.
- Live camera stream from Unity available.
- Base stability issue fixed (root anchoring script).

---

## Phase 1 — Planning Stack Baseline (Do this first)

### 1. Freeze a known-good baseline
- Keep this Unity scene + URDF as baseline branch/tag.
- Validation: arm and gripper move from ROS2 terminal commands.

### 2. Setup MoveIt 2 for UR10e
- Create/verify MoveIt config package for UR10e + gripper.
- Confirm planning group names (`manipulator`, `gripper`).
- Confirm collision geometry is reasonable.

### 3. Start with OMPL first (fast validation)
- Run planner and execute sample point-to-point plans.
- Validate self-collision + scene collision checks.
- Output: reliable planning/execution loop.

### 4. Add CHOMP after OMPL works
- Enable CHOMP pipeline in MoveIt config.
- Compare OMPL vs CHOMP trajectories for smoothness and clearance.
- Use CHOMP where optimization quality matters.

---

## Phase 2 — Perception Foundation (RGB-D)

### 5. Camera pipeline (2–3 RGB-D)
- Bring up all cameras in ROS2.
- Publish synchronized RGB + depth + camera_info.
- Validate frame rates and latency.

### 6. Calibration and TF
- Extrinsic calibration camera->robot base.
- Stable TF tree to `base_link`.
- Validate reprojection error and transform consistency.

### 7. Bin/object pose estimation
- Start simple: single known part, one bin.
- Segment/detect part and estimate 6D pose.
- Publish pick pose in robot frame.

---

## Phase 3 — Pick Pipeline Integration

### 8. Grasp candidate generation
- Define approach vector + pre-grasp + grasp + retreat poses.
- Add simple grasp heuristics first.

### 9. Plan and execute with scene updates
- Inject bins/obstacles into planning scene.
- Plan to pre-grasp -> grasp -> lift -> place.
- Add failure recovery and retries.

### 10. Scale up
- Multiple part types, cluttered bins, multi-camera fusion.
- Measure cycle time, success rate, failure modes.

---

## Immediate Next Session Checklist
1. Confirm MoveIt2 UR10e config package exists and launches.
2. Run one successful planned trajectory with OMPL.
3. Enable CHOMP and compare one trajectory.
4. Decide camera stack for RGB-D (model + ROS2 driver).

---

## Definition of Done (Milestone)
- Robot autonomously picks a known part from a bin using RGB-D perception.
- Planning uses MoveIt2 with CHOMP available/active for refined trajectories.
- End-to-end loop stable for repeated runs.
