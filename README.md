# ROS 2 RMW launch smoke test

This repository is a deliberately small CI probe for ROS 2 pub/sub communication.
It builds two packages and runs Python and C++ `launch_testing` tests against
three RMW implementations:

- `rmw_fastrtps_cpp`
- `rmw_cyclonedds_cpp`
- `rmw_zenoh_cpp`

The packages are named `rmw_launch_smoke_test_py` and
`rmw_launch_smoke_test_cpp` so that the implementation under test is explicit.
Both packages publish and receive the same five ordered `std_msgs/msg/String`
messages.

The GitHub Actions workflows use only ROS 2 Lyrical. The Windows workflow uses
the official binary archive and pixi, while the Ubuntu reference workflow uses
the ROS Tooling container described below. They provide one job per platform,
and each job runs the same three RMW cases sequentially. The test launches a
subscriber, then a publisher, and requires five ordered `std_msgs/msg/String`
messages. For Zenoh, the test also starts `rmw_zenohd`, because the RMW requires
a router for discovery.

## Windows setup

The workflow is the reference setup for this repository. It downloads the
official Windows archive, installs its pixi environment, runs the ROS-specific
Windows preparation script, and uses the Visual Studio x64 environment for
building and testing.

The following is an abbreviated local version. Run the download part in
PowerShell, then run the build and test commands from an x64 Native Tools
Command Prompt for Visual Studio 2022. Adjust the Visual Studio installation
path if the `Enterprise` edition is not installed.

```powershell
$ros2Prefix = Join-Path $PWD 'ros2_lyrical'
$ros2Archive = 'ros2-lyrical-2026-08-07-windows-AMD64.zip'
$ros2ReleaseTag = 'release-lyrical-20260807'
$ros2ReleaseUrl = "https://github.com/ros2/ros2/releases/download/$ros2ReleaseTag/$ros2Archive"

New-Item -ItemType Directory -Force -Path $ros2Prefix | Out-Null
Invoke-WebRequest -Uri $ros2ReleaseUrl -OutFile (Join-Path $ros2Prefix $ros2Archive)
Expand-Archive -Path (Join-Path $ros2Prefix $ros2Archive) -DestinationPath $ros2Prefix -Force
```

```bat
set ROS2_ROOT=%CD%\ros2_lyrical\ros2-windows
set PIXI_MANIFEST=%ROS2_ROOT%\pixi.toml

call "%ProgramFiles%\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat"
pixi install --manifest-path "%PIXI_MANIFEST%"
pixi run --manifest-path "%PIXI_MANIFEST%" python "%ROS2_ROOT%\preinstall_setup_windows.py"
call "%ROS2_ROOT%\setup.bat"
pixi run --manifest-path "%PIXI_MANIFEST%" colcon build --merge-install
call install\setup.bat

set RMW_IMPLEMENTATION=rmw_fastrtps_cpp
pixi run --manifest-path "%PIXI_MANIFEST%" colcon test --merge-install --event-handlers console_direct+
pixi run --manifest-path "%PIXI_MANIFEST%" colcon test-result --verbose
```

Set `RMW_IMPLEMENTATION` to `rmw_cyclonedds_cpp` or `rmw_zenoh_cpp` and repeat
the last two commands to exercise the other implementations. The GitHub
Actions workflow performs these three cases sequentially in one job, so the
ROS archive and pixi environment are created only once.

## Ubuntu container reference

`.github/workflows/launch-test-ubuntu.yml` is the reference implementation for
the normal Ubuntu behavior. It follows the same container/action pattern as the
reference workflow in `memfd_buffer_backend`: the job runs in
`rostooling/setup-ros-docker:ubuntu-resolute-ros-lyrical-ros-base-latest` and
uses `ros-tooling/action-ros-ci@v0.4`. The container already provides the
Lyrical ROS installation and build tools, so Ubuntu does not need the Windows
archive extraction or `preinstall_setup_windows.py` step.

The workflow invokes the action three times sequentially in the same job, once
for each `RMW_IMPLEMENTATION`. Each invocation performs the standard checkout,
dependency setup, build, and test flow for both packages. This intentionally
matches the simple `memfd_buffer_backend` CI style while avoiding a three-job
matrix.

Each package has an Ubuntu and Windows launch file under its `test/` directory.
The package CMake files select the platform-specific file. The Python package's
Ubuntu test uses `python3` to run the installed Python nodes. The C++ package
uses `launch_ros.actions.Node` to run its installed publisher and subscriber
executables. Both tests start the Zenoh router as a normal launch-managed
`ExecuteProcess` on Ubuntu; the Windows tests use separate router cleanup
because this assumption does not hold reliably there.

The C++ package runs `ament_lint_auto` on both platforms where the available
tools permit it. Its CMake file excludes `ament_cmake_clang_tidy` on Windows
because that check is not reliable in the ROS 2 Windows environment.

When using the standalone Lyrical Linux archive instead of the ROS Tooling
container, its `setup.bash` can reference optional variables such as
`COLCON_TRACE` without defining them first. Do not enable `set -u` in the shell
that sources ROS setup files; keep strict error checking in the outer command
or initialize the optional variables first. The container/action workflow does
not need this manual archive workaround.

## Findings and known Windows limitations

### Process shutdown is not equivalent to Ubuntu

Windows does not provide the same POSIX signal and process-group behavior as
Ubuntu. In particular, a `launch_testing` shutdown can cause a Python child to
report exit code `1` where a Linux process would report a negative signal exit
code such as `-2` or `-15`. A child process can also remain alive after the
launch test has finished. This can make the test assertions pass while CTest
still hangs or times out.

This behavior is discussed in [Properly close Windows processes](https://discourse.openrobotics.org/t/properly-close-windows-processes-discussion-about-implementation/57308).

The test currently accepts the Windows termination code `1` in addition to the
normal success and POSIX-style termination codes. This is deliberately scoped
to Windows; it does not weaken the assertion for unrelated non-zero exits.

### Executing installed Python nodes

On Windows, launching an installed `.py` file as if it were a native executable
can fail with `WinError 193`. The launch description therefore invokes the
Python interpreter resolved by `FindExecutable(name='python')` and passes the
installed script as an argument. This is different from the usual Linux pattern
of executing an installed script directly.

### Zenoh router cleanup

The first Windows implementation started `rmw_zenohd` as a launch-managed
process. Pub/sub assertions passed, but the router wrapper/child process could
survive launch shutdown and cause the 45-second CTest timeout.

The current workaround starts the Zenoh router with `subprocess.Popen` outside
the launch process list. The post-shutdown test uses `psutil` to terminate the
router and its descendant processes, waits briefly, and kills any remaining
processes. This makes the Windows workflow complete reliably while keeping the
router cleanup explicit.

### Fast DDS configuration

This smoke test uses one ROS domain and local pub/sub only. No additional Fast
DDS configuration file is required for the current test. More complex tests
may still need middleware-specific configuration or discovery settings.

## Possible future approaches

The explicit `psutil` cleanup is a test-level workaround, not a general fix for
ROS 2 process management. Other approaches worth evaluating are:

- improving `launch`/`launch_testing` Windows shutdown and process-tree handling;
- supervising each test process with a Windows Job Object or an equivalent
  process-group mechanism;
- making middleware helper processes part of a dedicated fixture with a clear
  lifetime, rather than treating them as ordinary launch actions;
- adding a small Windows-specific integration test for orphan detection and
  shutdown completion.

The last two options may be useful when a test needs more than the single
Zenoh router used here.

## Ubuntu local test

The CI container can also be used locally. From the repository root:

```bash
docker run --rm -it \
  -v "$PWD:/work/src/rmw_launch_smoke_test" \
  -w /work \
  rostooling/setup-ros-docker:ubuntu-resolute-ros-lyrical-ros-base-latest \
  bash

source /opt/ros/lyrical/setup.bash
colcon build --merge-install --cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
source install/local_setup.bash

for rmw in rmw_fastrtps_cpp rmw_cyclonedds_cpp rmw_zenoh_cpp; do
  RMW_IMPLEMENTATION="$rmw" colcon test --merge-install \
    --event-handlers console_direct+
  colcon test-result --verbose
done
```

The Windows workflow is intentionally separate: it uses `setup.bat`, the Visual
Studio environment, a Windows archive, pixi, and the Windows-specific shutdown
behavior described above. Ubuntu is container-based so its base operating
system and ROS-related dependencies remain easier to reproduce.
