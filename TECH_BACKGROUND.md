
A. 当前技术摸底（tech background on what we knew and tested）

We have validated on Jetson Orin that our 20MP UVC camera can stream MJPEG at 5120×3840 and 27.5 FPS through a GStreamer pipeline based on v4l2src, jpegparse, nvv4l2decoder, and nvvidconv, with successful downscaled real-time preview at 720p. This confirms that, on Orin, the high-resolution UVC MJPEG capture and hardware-accelerated decode path are feasible and stable enough for the intended dual-camera GUI preview workflow. Based on this, the recommended architecture is to keep a low-latency preview branch for embedded GUI display and a separate raw MJPEG capture branch using appsink, so that full-resolution 20MP JPEG frames can be saved directly to local files on user-triggered capture without re-encoding.  ￼

1. 目标场景已经明确

你的目标不是单路 demo，而是：
	•	两路 USB UVC 相机
	•	每路输出 MJPEG, 5120×3840, 27.5 FPS
	•	在 Jetson Orin 上做
	•	GUI 内部实时预览时，显示分辨率降到 720p
	•	用户点击拍照时，分别把两路相机的原始全分辨率 MJPEG 单帧直接写入本地文件，也就是保存成两张 20MP .jpg

这意味着系统其实分成两条逻辑链：
	•	预览链：低分辨率、低延迟、持续运行
	•	抓拍链：不重编码，直接保存最新原始 MJPEG 帧

这个思路和 Jetson 官方的 Accelerated GStreamer 能力是匹配的：Jetson 上有 nvv4l2decoder 做 JPEG/MJPEG 硬解，有 nvvidconv 做缩放和格式转换，有 nveglglessink 做显示。 ￼

2. 我们已经排除了一个关键误区：nvv4l2camerasrc 不是你的主路线

前面你担心普通 v4l2src 在高分辨率 UVC MJPEG 下可能不稳，想考虑 nvv4l2camerasrc 替代。但从官方文档定位看，nvv4l2camerasrc 并不是面向“通用 USB UVC MJPEG source”的最佳入口；Jetson 官方加速插件列表里虽然有它，但你当前已经实测证明 v4l2src + image/jpeg + jpegparse + nvv4l2decoder 是可工作的。对于你这个具体相机和这个具体平台，继续沿用 v4l2src 已经是更确定的路线。 ￼

3. 最关键的实测结论：Orin 上主链路已跑通

你已经实测跑通了这条命令：

gst-launch-1.0 -v v4l2src device=/dev/video0 ! \
  image/jpeg,width=5120,height=3840,framerate=55/2 ! \
  jpegparse ! nvv4l2decoder mjpeg=1 ! \
  nvvidconv ! 'video/x-raw(memory:NVMM),width=1280,height=720,format=NV12' ! \
  nveglglessink sync=false

这件事说明了非常多信息：
	•	v4l2src 能和这台 UVC 相机在 5120×3840 @ 27.5fps MJPEG 模式下完成协商
	•	jpegparse + nvv4l2decoder mjpeg=1 在 Orin 上能正确解码这路流
	•	nvvidconv 能把 20MP 流缩到 720p 用于预览
	•	nveglglessink 可以把视频实时显示出来

也就是说，你之前在 RK3588 上遇到的 not-negotiated，并没有在 Orin 上复现为主阻塞问题。对现在这个项目而言，底层“能不能取到并显示 5K MJPEG UVC 流”已经不是未知数，而是已验证通过。Jetson 官方文档也确实把 nvv4l2decoder 列为支持 JPEG/MJPEG 解码的插件，把 nvvidconv 列为缩放/格式转换插件，把 nveglglessink 列为 EGL/GLES 显示 sink。 ￼

4. 现在真正的问题已经从“媒体兼容性”转向“应用集成”

你接下来的核心问题不再是：
	•	用不用 nvv4l2camerasrc
	•	Orin 能不能跑这路流
	•	MJPEG 能不能硬解

而变成了：
	•	如何做两路并行
	•	如何把预览嵌入 GUI 内部
	•	如何在点击拍照时拿到最新原始 MJPEG 单帧
	•	如何保证抓拍时不影响预览
	•	如何管理双相机同步保存、命名、异常恢复

其中“嵌入 GUI 内部”这件事，在 GStreamer 体系内通常是通过 VideoOverlay 接口把视频 sink 绑定到应用窗口来做；“应用拿到一帧做自定义处理/保存”则通常通过 appsink 来做。GStreamer 官方文档明确说明了 GstVideoOverlay 用于把视频渲染到应用窗口，appsink 用于让应用直接拿到 pipeline 数据。 ￼

⸻

