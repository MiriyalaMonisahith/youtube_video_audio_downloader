import cv2

def auto_zoom(input_path, output_path):

    cap = cv2.VideoCapture(input_path)

    fps = cap.get(cv2.CAP_PROP_FPS)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    out = cv2.VideoWriter(
        output_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (1080, 1920)
    )

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        h, w, _ = frame.shape

        # simple smart center (upgradeable to face detection later)
        cx, cy = w // 2, h // 2

        crop_w = int(h * 9 / 16)

        x1 = max(0, cx - crop_w // 2)
        x2 = x1 + crop_w

        cropped = frame[:, x1:x2]

        resized = cv2.resize(cropped, (1080, 1920))

        out.write(resized)

    cap.release()
    out.release()