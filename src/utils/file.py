import io
import json
import os
import pickle
import sys
import time
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from pprint import pprint
from typing import Any, Dict, Mapping

import pandas as pd
import yaml
from pydantic import ValidationError


logger = get_logger(__name__)


def load(path) -> Any:
    extension = path.split(".")[-1]
    try:
        if extension == "txt":
            with open(path, "r", encoding="utf-8") as f:
                loaded_file = f.read()
        elif extension == "csv":
            with open(path, "r", encoding="utf-8") as f:
                loaded_file = pd.read_csv(f, encoding="utf-8")
        elif extension == "json":
            with open(path, "r", encoding="utf-8") as f:
                loaded_file = json.load(f)
        elif extension == "yaml":
            with open(path, "r", encoding="utf-8") as f:
                loaded_file = yaml.safe_load(f)
        elif extension == "pkl":
            with open(path, "rb") as f:
                loaded_file = pickle.load(f)
        else:
            raise UtilsValidationError(
                f"Unsupported file extension: {extension}",
                details={"extension": extension},
            )
        return loaded_file
    except Exception as e:
        raise UtilsIOError(
            f"Error loading file: {e}",
            details={"path": path, "extension": extension},
        ) from e


def save(data: Any, path: str):
    parent_dir = os.path.dirname(path)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)

    # print(f"Saving file to: {path}")
    sub_folder = os.path.basename(path)
    extension = sub_folder.split(".")[-1]
    try:
        if extension == "txt":
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(data)
        elif extension == "csv":
            if isinstance(data, pd.DataFrame):
                with open(path, "w", encoding="utf-8-sig") as f:
                    data.to_csv(f, index=False, encoding="utf-8-sig")
            else:
                raise UtilsValidationError(
                    "Data must be a pandas DataFrame for CSV format.",
                    details={"expected_type": "pandas.DataFrame"},
                )
        elif extension == "json":
            with open(path, "w", encoding="utf-8-sig") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        elif extension == "yaml":
            with open(path, "w", encoding="utf-8-sig") as f:
                yaml.dump(data, f, allow_unicode=True, sort_keys=False)
        elif extension == "pkl":
            with open(path, "wb") as f:
                pickle.dump(data, f)
        else:
            raise UtilsValidationError(
                f"Unsupported file extension: {extension}",
                details={"extension": extension},
            )
    except Exception as e:
        logger.exception("Error saving file to %s", path)


def _to_triple_quoted(s: str) -> str:
    # 내부에 """가 있으면 \"\"\"로 이스케이프하여 소스가 깨지지 않게 함
    body = s.replace('"""', '\\"""')
    return f'"""{body}"""'


def _to_python_literal(v: Any) -> str:
    """
    파이썬 파일에 쓸 수 있는 안전한 리터럴 텍스트로 변환.
    - str: 멀티라인 또는 제어문자 많으면 삼중따옴표, 아니면 repr
    - 기타(리스트/딕셔너리 등): pprint로 예쁘게 포맷
    """
    if isinstance(v, str):
        # 멀티라인이거나 탭/백슬래시 등 제어문자가 많을 때 가독성 위해 삼중따옴표
        if "\n" in v or "\r" in v:
            return _to_triple_quoted(v)
        # 한 줄이면 repr 사용 (자동 이스케이프 + 단따옴표 사용)
        return repr(v)
    elif isinstance(v, (int, float, bool)) or v is None:
        return repr(v)
    else:
        # 복합 구조는 파이썬 리터럴로 예쁘게
        return pprint.pformat(v, width=100, sort_dicts=False)


def save_dict_as_py(
    data: Dict[str, Any],
    path: str,
    *,
    overwrite: bool = False,
    sort_keys: bool = False,
    header_comment: str | None = "# -*- coding: utf-8 -*-",
) -> None:
    """
    dict의 각 key를 파이썬 변수로 저장.
    - key는 유효한 식별자여야 함 (필요시 직접 정제해서 넘겨주세요)
    - 값은 파이썬 리터럴로 안전하게 직렬화
    """
    if os.path.exists(path) and not overwrite:
        logger.info("File %s already exists. Skipping to avoid overwrite.", path)
    else:
        dirpath = os.path.dirname(path)
        if dirpath and not os.path.exists(dirpath):
            os.makedirs(dirpath)

        keys = sorted(data.keys()) if sort_keys else list(data.keys())
        try:
            with io.open(path, "w", encoding="utf-8", newline="\n") as f:
                if header_comment:
                    f.write(f"{header_comment}\n\n")
                for k in keys:
                    v = data[k]
                    literal = _to_python_literal(v)
                    # 가독성을 위해 멀티라인이면 한 줄 비우고 작성
                    if isinstance(v, str) and ("\n" in v or "\r" in v):
                        f.write(f"{k} = {literal}\n\n")
                    else:
                        f.write(f"{k} = {literal}\n")
            logger.info("Saved dict to %s", path)
        except Exception as e:
            logger.exception("Error saving dict to %s", path)
            raise


def load_prompts_from_module(
    prompt_filename: str, *, include_private: bool = False
) -> dict[str, str]:
    if not prompt_filename.endswith(".py"):
        prompt_filename = f"{prompt_filename}.py"

    root_dir = Path(__file__).resolve().parents[2]
    prompts_path = root_dir / "src" / "prompts" / prompt_filename

    if not prompts_path.exists():
        raise UtilsNotFoundError(
            f"Prompt file not found: {prompts_path}",
            details={"path": str(prompts_path)},
        )

    module_name = f"_dynamic_prompts_{prompts_path.stem}_{int(time.time_ns())}"
    spec = spec_from_file_location(module_name, prompts_path)
    if spec is None or spec.loader is None:
        raise UtilsIOError(
            f"Could not load prompts from: {prompts_path}",
            details={"path": str(prompts_path)},
        )

    module = module_from_spec(spec)
    prompts: dict[str, str] = {}
    try:
        sys.modules[module_name] = module  # type: ignore[assignment]
        spec.loader.exec_module(module)  # type: ignore[arg-type]
        for name, value in vars(module).items():
            if isinstance(value, str) and (include_private or not name.startswith("_")):
                prompts[name] = value
    finally:
        sys.modules.pop(module_name, None)

    return prompts


def require_prompt(prompts: Mapping[str, str], key: str) -> str:
    prompt = prompts.get(key)
    if prompt is None:
        available = ", ".join(sorted(prompts)) if prompts else "<none>"
        raise UtilsValidationError(
            f"Prompt '{key}' not found.",
            details={"requested_key": key, "available": available},
        )
    return prompt


def load_config(config_path: str | Path | None = None) -> AppConfig:
    if config_path is None:
        # Default to this module's config directory when no path is provided
        config_root = Path(__file__).resolve().parents[2]
        config_path = config_root / "config" / "config.yaml"

    raw_config = load(str(config_path))
    if not isinstance(raw_config, dict):
        raise UtilsConfigurationError(
            "Configuration file must contain a top-level mapping.",
            details={"path": str(config_path)},
        )

    try:
        return AppConfig.model_validate(raw_config)
    except ValidationError as error:
        raise UtilsConfigurationError(
            f"Invalid configuration: {error}",
            details={"path": str(config_path)},
        ) from error
