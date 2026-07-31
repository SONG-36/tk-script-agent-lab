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
        {
            SRC_ROOT / "knowledge" / "contracts.py": imports_for(
                SRC_ROOT / "knowledge" / "contracts.py"
            ),
            SRC_ROOT / "knowledge" / "ingestion_contracts.py": imports_for(
                SRC_ROOT / "knowledge" / "ingestion_contracts.py"
            ),
            SRC_ROOT / "knowledge" / "index_contracts.py": imports_for(
                SRC_ROOT / "knowledge" / "index_contracts.py"
            ),
            SRC_ROOT / "knowledge" / "embedding_contracts.py": imports_for(
                SRC_ROOT / "knowledge" / "embedding_contracts.py"
            ),
            SRC_ROOT / "knowledge" / "vector_store_contracts.py": imports_for(
                SRC_ROOT / "knowledge" / "vector_store_contracts.py"
            ),
        },
        (
            "langgraph",
            "langchain_openai",
            "openai",
            "yaml",
            "tk_script_agent_lab.prompts",
            "scripts",
            "tests",
        ),
    )


def test_phase_4c_adapters_do_not_import_graph_prompts_or_providers() -> None:
    assert_no_imports(
        {
            SRC_ROOT / "knowledge" / "openai_embedding.py": imports_for(
                SRC_ROOT / "knowledge" / "openai_embedding.py"
            ),
            SRC_ROOT / "knowledge" / "qdrant_vector_store.py": imports_for(
                SRC_ROOT / "knowledge" / "qdrant_vector_store.py"
            ),
            SRC_ROOT / "knowledge" / "vector_retriever.py": imports_for(
                SRC_ROOT / "knowledge" / "vector_retriever.py"
            ),
        },
        (
            "langgraph",
            "tk_script_agent_lab.prompts",
            "tk_script_agent_lab.providers",
            "scripts",
        ),
    )


def test_phase_4b_modules_do_not_import_runtime_or_vector_dependencies() -> None:
    assert_no_imports(
        {
            SRC_ROOT / "knowledge" / "in_memory_index.py": imports_for(
                SRC_ROOT / "knowledge" / "in_memory_index.py"
            ),
            SRC_ROOT / "knowledge" / "exact_retriever.py": imports_for(
                SRC_ROOT / "knowledge" / "exact_retriever.py"
            ),
            SRC_ROOT / "knowledge" / "retrieval_eval.py": imports_for(
                SRC_ROOT / "knowledge" / "retrieval_eval.py"
            ),
        },
        (
            "langgraph",
            "langchain_openai",
            "openai",
            "faiss",
            "chromadb",
            "qdrant",
            "pinecone",
            "pymilvus",
            "tk_script_agent_lab.prompts",
            "tk_script_agent_lab.providers",
            "scripts",
        ),
    )


def test_langgraph_app_does_not_depend_on_phase_4b_index_or_eval() -> None:
    assert_no_imports(
        package_imports("langgraph_app"),
        (
            "tk_script_agent_lab.knowledge.index_contracts",
            "tk_script_agent_lab.knowledge.in_memory_index",
            "tk_script_agent_lab.knowledge.exact_retriever",
            "tk_script_agent_lab.knowledge.retrieval_eval",
            "tk_script_agent_lab.knowledge.openai_embedding",
            "tk_script_agent_lab.knowledge.qdrant_vector_store",
            "tk_script_agent_lab.knowledge.vector_retriever",
        ),
    )


def test_phase_4d_pack_document_adapter_has_no_runtime_dependencies() -> None:
    assert_no_imports(
        {
            SRC_ROOT / "knowledge" / "creative_pack_documents.py": imports_for(
                SRC_ROOT / "knowledge" / "creative_pack_documents.py"
            )
        },
        (
            "langgraph",
            "langchain_openai",
            "openai",
            "tk_script_agent_lab.prompts",
            "tk_script_agent_lab.providers",
            "scripts",
        ),
    )


def test_phase_4d_query_builder_has_no_runtime_adapter_dependencies() -> None:
    assert_no_imports(
        {
            SRC_ROOT / "knowledge" / "creative_retrieval_query.py": imports_for(
                SRC_ROOT / "knowledge" / "creative_retrieval_query.py"
            )
        },
        (
            "langgraph",
            "langchain_openai",
            "openai",
            "qdrant_client",
            "tk_script_agent_lab.prompts",
            "scripts",
        ),
    )


def test_phase_4d_vector_runtime_does_not_import_graph_prompts_or_creative_providers() -> None:
    assert_no_imports(
        {
            SRC_ROOT / "knowledge" / "creative_vector_runtime.py": imports_for(
                SRC_ROOT / "knowledge" / "creative_vector_runtime.py"
            )
        },
        (
            "langgraph",
            "tk_script_agent_lab.prompts",
            "tk_script_agent_lab.providers",
            "scripts",
        ),
    )


def test_openai_creative_provider_does_not_import_phase_4d_runtime() -> None:
    assert_no_imports(
        {
            SRC_ROOT / "providers" / "openai_creative.py": imports_for(
                SRC_ROOT / "providers" / "openai_creative.py"
            )
        },
        ("tk_script_agent_lab.knowledge.creative_vector_runtime",),
    )


def test_src_does_not_read_phase_4b_fixture_files() -> None:
    violations = [
        str(path)
        for path in SRC_ROOT.rglob("*.py")
        if "rag_retrieval_v1" in path.read_text(encoding="utf-8")
    ]
    assert violations == []


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
