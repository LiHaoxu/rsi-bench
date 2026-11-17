#!/usr/bin/env python3
"""Validate a measured result record; no experiment is run by this script."""
import argparse
from datetime import date
import json
import math
from pathlib import Path
import re
import statistics
import sys
from urllib.parse import urlparse

PROTOCOLS = {"offline-self-training", "continual-temporal", "interactive-policy", "agent-feedback"}


def validate(record):
    errors = []

    def check(condition, message):
        if not condition:
            errors.append(message)
        return condition

    def text(value, name):
        return check(isinstance(value, str) and bool(value.strip()) and value.strip().lower() not in {"todo", "tbd", "unknown", "placeholder", "待填写"}, f"{name}: 需要非空的实测信息")

    def number(value, name, *, nonnegative=True):
        constraint = "有限的非负数" if nonnegative else "有限数值"
        return check(type(value) in (int, float) and math.isfinite(value) and (not nonnegative or value >= 0), f"{name}: 必须为{constraint}，不能为 null")

    def https_url(value, name):
        if not isinstance(value, str):
            return check(False, f"{name}: 需要 HTTPS URL")
        parts = urlparse(value)
        return check(parts.scheme == "https" and bool(parts.hostname) and "." in parts.hostname and parts.username is None and not parts.hostname.endswith(".example") and parts.hostname not in {"example.com", "example.org", "example.net"}, f"{name}: 需要实际的 HTTPS URL")

    if not isinstance(record, dict):
        return ["结果必须为 JSON 对象"]
    check(record.get("schema_version") == 1, "schema_version: 必须为 1")
    check(record.get("status") == "measured", "status: 只有 measured 记录可收录；未运行模板不可提交为结果")
    for name in ("id", "method"):
        text(record.get(name), name)
    check(isinstance(record.get("id"), str) and bool(re.fullmatch(r"[a-z0-9][a-z0-9_-]*", record.get("id", ""))), "id: 使用小写字母、数字、下划线或短横线")
    https_url(record.get("repository"), "repository")
    check(isinstance(record.get("commit"), str) and bool(re.fullmatch(r"[0-9a-fA-F]{40}", record.get("commit", ""))), "commit: 需要完整的 40 位 Git commit SHA")
    check(isinstance(record.get("protocol"), str) and record["protocol"] in PROTOCOLS, "protocol: 需要已定义的协议 ID")
    try:
        date.fromisoformat(record.get("measured_at", ""))
    except (ValueError, TypeError):
        errors.append("measured_at: 需要 YYYY-MM-DD 测量日期")
    dataset = record.get("dataset")
    if check(isinstance(dataset, dict), "dataset: 需要数据集对象"):
        for name in ("name", "version", "split", "candidate_protocol"):
            text(dataset.get(name), "dataset." + name)
    seeds = record.get("seeds")
    seed_ok = isinstance(seeds, list) and len(seeds) >= 3 and all(type(s) is int and s >= 0 for s in seeds) and len(set(seeds)) == len(seeds)
    check(seed_ok, "seeds: 至少 3 个互不重复的非负整数 seed")
    rounds = record.get("rounds")
    round_ok = check(isinstance(rounds, list) and len(rounds) >= 2, "rounds: 至少需要第 0 轮和 1 个更新轮次")
    round_ids, metric_names = [], None
    if round_ok:
        for i, result_round in enumerate(rounds):
            prefix = f"rounds[{i}]"
            if not check(isinstance(result_round, dict), prefix + ": 需要对象"):
                continue
            round_id = result_round.get("round")
            if check(type(round_id) is int and round_id >= 0, prefix + ".round: 需要非负整数"):
                round_ids.append(round_id)
            metrics = result_round.get("metrics")
            if not check(isinstance(metrics, dict) and bool(metrics), prefix + ".metrics: 需要至少一个指标"):
                continue
            if metric_names is None:
                metric_names = set(metrics)
            else:
                check(set(metrics) == metric_names, prefix + ".metrics: 各轮必须提供相同指标")
            for metric, values in metrics.items():
                key = prefix + ".metrics." + str(metric)
                text(metric, key + " 名称")
                if not check(isinstance(values, dict), key + ": 需要 mean、std 和 per_seed"):
                    continue
                mean_ok = number(values.get("mean"), key + ".mean", nonnegative=False)
                std_ok = number(values.get("std"), key + ".std")
                per_seed = values.get("per_seed")
                if not check(isinstance(per_seed, list), key + ".per_seed: 需要逐 seed 的测量列表"):
                    continue
                seen, valid_values = [], []
                for j, row in enumerate(per_seed):
                    if not check(isinstance(row, dict), key + f".per_seed[{j}]: 需要对象"):
                        continue
                    seen.append(row.get("seed"))
                    if number(row.get("value"), key + f".per_seed[{j}].value", nonnegative=False):
                        valid_values.append(row["value"])
                check(seed_ok and len(seen) == len(seeds) and all(type(s) is int for s in seen) and sorted(seen) == sorted(seeds), key + ".per_seed: 需要恰好覆盖全部 seeds")
                if len(valid_values) >= 3 and len(valid_values) == len(per_seed):
                    if mean_ok:
                        check(math.isclose(values["mean"], statistics.mean(valid_values), rel_tol=1e-5, abs_tol=1e-8), key + ".mean: 与逐 seed 均值不一致")
                    if std_ok:
                        check(math.isclose(values["std"], statistics.stdev(valid_values), rel_tol=1e-5, abs_tol=1e-8), key + ".std: 与逐 seed 样本标准差不一致")
        check(len(round_ids) == len(rounds) and len(set(round_ids)) == len(rounds) and 0 in round_ids and round_ids == sorted(round_ids), "rounds: 轮次必须唯一、递增并包含第 0 轮")
    cost = record.get("cost")
    if check(isinstance(cost, dict), "cost: 需要实际成本对象"):
        for name in ("training_seconds", "generation_seconds", "total_gpu_hours", "llm_tokens"):
            number(cost.get(name), "cost." + name)
        check(type(cost.get("llm_tokens")) is int, "cost.llm_tokens: 必须为整数，未调用 LLM 时填写 0")
    https_url(record.get("evidence_artifact_url"), "evidence_artifact_url")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path, help="单条实测结果 JSON；模板应当校验失败")
    args = parser.parse_args()
    try:
        record = json.loads(args.result.read_text(encoding="utf-8"))
        errors = validate(record)
    except (OSError, ValueError, TypeError) as error:
        print(f"读取失败: {error}", file=sys.stderr)
        return 1
    if errors:
        print("未通过结果校验：", file=sys.stderr)
        for message in errors:
            print("- " + message, file=sys.stderr)
        return 1
    print("结构与数值一致性校验通过；仍需人工核验实验代码、日志及可复现性。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
