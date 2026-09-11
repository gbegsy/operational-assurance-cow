from pathlib import Path

# Execute the application source without Streamlit's top-level expression
# transformation. This keeps conditional UI expressions from being rendered
# as DeltaGenerator objects in the page.
source = (Path(__file__).parent / "app.py").read_text(encoding="utf-8")
exec(compile(source, "app.py", "exec"), {"__name__": "__main__", "__file__": str(Path(__file__).parent / "app.py")})
