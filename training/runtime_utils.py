from __future__ import annotations


def detect_device(torch, requested: str = "auto") -> str:
    if requested != "auto":
        return requested
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def pick_precision(torch, requested: str, device: str | None = None) -> tuple[bool, bool]:
    device = device or detect_device(torch)
    if requested == "bf16":
        return (device == "cuda"), False
    if requested == "fp16":
        return False, (device == "cuda")
    if requested == "fp32":
        return False, False
    if device != "cuda":
        return False, False
    major, _minor = torch.cuda.get_device_capability()
    if major >= 8:
        return True, False
    return False, True


def pick_model_dtype(torch, device: str, requested: str = "auto"):
    if requested == "fp16":
        return torch.float16
    if requested == "bf16":
        return torch.bfloat16
    if requested == "fp32":
        return torch.float32
    if device == "cuda":
        use_bf16, use_fp16 = pick_precision(torch, "auto", device=device)
        if use_bf16:
            return torch.bfloat16
        if use_fp16:
            return torch.float16
    if device == "mps":
        return torch.float16
    return torch.float32
