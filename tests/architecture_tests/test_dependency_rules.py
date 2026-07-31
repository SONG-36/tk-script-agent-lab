import ast
from pathlib import Path


SRC_ROOT = Path("src/tk_script_agent_lab")


def imports_for(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def package_imports(package: str) -> dict[Path, set[str]]:
    return {
        path: imports_for(path)
        for path in (SRC_ROOT / package).rglob("*.py")
    }


def assert_no_imports(imports_by_file: dict[Path, set[str]], forbidden: tuple[str, ...]) -> None:
    violations = []
    for path, imports in imports_by_file.items():
        for imported in imports:
            if imported.startswith(forbidden):
                violations.append(f"{path}: {imported}")
    assert violations == []


def test_domain_has_no_framework_or_adapter_imports() -> None:
    assert_no_imports(
        package_imports("domain"),
        (
            "langgraph",
            "langchain_openai",
            "openai",
            "yaml",
            "tk_script_agent_lab.providers",
            "tk_script_agent_lab.langgraph_app",
            "scripts",
            "tests",
        ),
    )


def test_knowledge_contracts_have_no_runtime_adapter_imports() -> None:
    assert_no_imports(
        {SRC_ROOT / "knowledge" / "contracts.py": imports_for(SRC_ROOT / "knowledge" / "contracts.py")},
        (
            "langgraph",
            "langchain_openai",
            "openai",
            "yaml",
            "tk_script_agent_lab.prompts",
            "scripts",
        ),
    )


def test_providers_do_not_import_graph_scripts_or_tests() -> None:
    assert_no_imports(
        package_imports("providers"),
        (
            "tk_script_agent_lab.langgraph_app",
            "scripts",
            "tests",
        ),
    )


def test_src_does_not_import_experiments_or_docs() -> None:
    imports_by_file = {
        path: imports_for(path)
        for path in SRC_ROOT.rglob("*.py")
    }

    assert_no_imports(imports_by_file, ("scripts", "tests", "docs"))
