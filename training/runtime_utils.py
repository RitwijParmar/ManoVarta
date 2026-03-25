from __future__ import annotations


def pick_precision(torch, requested: str) -> tuple[bool, bool]:
    if requested == "bf16":
        return True, False
    if requested == "fp16":
        return False, True
    if requested == "fp32":
        return False, False
    if not torch.cuda.is_available():
        return False, False
    major, _minor = torch.cuda.get_device_capability()
    if major >= 8:
        return True, False
    return False, True
