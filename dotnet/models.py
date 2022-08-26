import dataclasses


@dataclasses.dataclass(eq=True)
class DotNetExample:
    target_filename: str
    target_dir: str
    content: str
