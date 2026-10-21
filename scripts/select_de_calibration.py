"""Fail-closed calibration selection using four development functions only.

No evaluation-function observations are accepted by this procedure.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from itertools import pairwise
from pathlib import Path

from run_tuned_de_jde import CANDIDATES, DEV_FUNCTIONS, DEV_SEED

from boundevo.cec2017 import REFERENCE_COMMIT

LABELS = tuple(c[0] for c in CANDIDATES)


def read_csv(path: Path) -> list[dict]:
    if not path.is_file():
        raise ValueError(f"missing original calibration evidence {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def calibrate(root: Path) -> tuple[dict, list[dict], list[dict]]:
    trials: list[dict] = []
    histories: list[dict] = []
    provenance = []
    sha = None
    for fid in DEV_FUNCTIONS:
        folder = root/f"f{fid}"
        manifest = json.loads((folder/"manifest.json").read_text(encoding="utf-8"))
        fixed = {
            "phase":"development","task_id":fid,"functions":[fid],
            "methods":list(LABELS),"dimension":30,"repeats":3,"seed_base":DEV_SEED,
            "evaluations":10000,"population":100,"history_step_fe":100,
            "reference_commit":REFERENCE_COMMIT,
        }
        if any(manifest.get(k)!=v for k,v in fixed.items()):
            raise ValueError(f"misconfigured development trial F{fid}")
        if not manifest.get("source_commit") or (
            sha is not None and sha!=manifest["source_commit"]
        ):
            raise ValueError("calibration shards came from different source versions")
        sha=manifest["source_commit"]
        provenance.append(manifest)
        rows=read_csv(folder/"trials.csv")
        h=read_csv(folder/"history.csv")
        if len(rows)!=18 or len(h)!=1800:
            raise ValueError("calibration original trial/checkpoint coverage is incomplete")
        trials.extend(rows)
        histories.extend(h)
    expected={(fid,repeat,method) for fid in DEV_FUNCTIONS
              for repeat in range(3) for method in LABELS}
    indexed={}
    for trial in trials:
        key=(int(trial["function_id"]),int(trial["repeat"]),trial["method"])
        if key not in expected or key in indexed:
            raise ValueError("unexpected/duplicate calibration key")
        fid, repeat, _=key
        if (int(trial["seed"])!=DEV_SEED+10000*fid+repeat
                or int(trial["evaluations"])!=10000
                or int(trial["dimension"])!=30 or float(trial["optimum"])!=100*fid
                or not math.isfinite(float(trial["error"]))
                or float(trial["error"])<0):
            raise ValueError("invalid original calibration FE, objective or seed")
        if not math.isclose(
            float(trial["objective"])-float(trial["optimum"]),
            float(trial["error"]),rel_tol=1e-10,abs_tol=1e-6
        ):
            raise ValueError("calibration CEC optimum mismatch")
        indexed[key]=trial
    if len(trials)!=72 or set(indexed)!=expected:
        raise ValueError("72 unique calibration trials required")
    sequences=defaultdict(list)
    for row in histories:
        key=(int(row["function_id"]),int(row["repeat"]),row["method"])
        if key not in expected or int(row["seed"])!=int(indexed[key]["seed"]):
            raise ValueError("unknown/mislabeled calibration original history")
        sequences[key].append(row)
    if len(histories)!=7200 or set(sequences)!=expected:
        raise ValueError("original 7200 calibration checkpoints required")
    for key, sequence in sequences.items():
        sequence.sort(key=lambda row:int(row["evaluations"]))
        fes=[int(row["evaluations"]) for row in sequence]
        vals=[float(row["best_error"]) for row in sequence]
        if (fes!=list(range(100,10001,100))
                or any(not math.isfinite(v) or v<0 for v in vals)
                or any(b>a+1e-7 for a,b in pairwise(vals))
                or not math.isclose(vals[-1],float(indexed[key]["error"]),
                                    rel_tol=1e-10,abs_tol=1e-6)):
            raise ValueError("corrupt best-so-far calibration curve")
    for fid in DEV_FUNCTIONS:
        for repeat in range(3):
            originals=[float(sequences[(fid,repeat,m)][0]["best_error"]) for m in LABELS]
            if max(originals)-min(originals)>1e-7:
                raise ValueError("different initial individuals in matched calibration")
    table=[]
    ranks_by_candidate=defaultdict(list)
    for fid in DEV_FUNCTIONS:
        means={
            m:statistics.fmean(float(indexed[(fid,repeat,m)]["error"])
                                for repeat in range(3))
            for m in LABELS
        }
        ranked=sorted(means.items(),key=lambda kv:(kv[1],LABELS.index(kv[0])))
        for m,value in ranked:
            rank=1+sum(v<value for v in means.values())+(
                sum(v==value for v in means.values())-1
            )/2
            ranks_by_candidate[m].append(rank)
            table.append({
                "function_id":fid, "candidate_id":m,"mean_error":value,
                "mean_rank":rank,"three_seeds":3,
            })
    board=[
        {"candidate_id":m,"average_development_function_rank":
         statistics.fmean(ranks_by_candidate[m]),
         "four_development_functions":len(DEV_FUNCTIONS)}
        for m in LABELS
    ]
    selected=min(
        LABELS,
        key=lambda m: (statistics.fmean(ranks_by_candidate[m]),LABELS.index(m))
    )
    chosen=next(c for c in CANDIDATES if c[0]==selected)
    digest=hashlib.sha256(
        json.dumps(sorted([
            (r["function_id"],r["method"],r["repeat"],r["error"]) for r in trials
        ]),separators=(",",":")).encode("utf-8")
    ).hexdigest()
    selection={
        "selected":selected,"strategy":chosen[1],
        "mutation":chosen[2],"crossover":chosen[3],
        "development_functions":list(DEV_FUNCTIONS),
        "calibration_trials":72,"calibration_histories":7200,
        "calibration_seed_base":DEV_SEED,
        "calibration_source_commit":sha,
        "calibration_data_sha256":digest,
        "selection_rule":"minimize mean of four per-function mean-error ranks; tied IDs by fixed candidate order",
        "source_manifests":provenance,
        "all_candidate_mean_ranks":{
            m:statistics.fmean(ranks_by_candidate[m]) for m in LABELS
        },
    }
    return selection,table,board


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--input-dir",type=Path,required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    args=p.parse_args()
    choice,per_function,board=calibrate(args.input_dir)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    (args.output_dir/"selection.json").write_text(
        json.dumps(choice,indent=2)+"\n",encoding="utf-8"
    )
    for name,rows in (("candidate_mean_ranks.csv",board),
                      ("candidate_function_scores.csv",per_function)):
        with (args.output_dir/name).open("w",newline="",encoding="utf-8") as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    print(f"Selected development-only DE candidate {choice['selected']}.")
    print("Verified 72 calibration trials and 7200 real objective checkpoints.")


if __name__=="__main__":
    main()
