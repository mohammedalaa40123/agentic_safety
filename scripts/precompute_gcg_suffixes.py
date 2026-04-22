#!/usr/bin/env python3
"""
Pre-compute GCG adversarial suffixes for every sample in a dataset.

Uses MPS (Apple Silicon) or CUDA if available; falls back to CPU with
reduced parameters.  Results are saved incrementally so the script can
be interrupted and resumed with --resume.

Output schema: data/gcg_cache_<dataset_stem>.json
  { "<sample_id>": "<suffix_string>", ... }

Usage:
    python scripts/precompute_gcg_suffixes.py \
        --dataset owasp_agentic_500_jailbreaks_v2.json \
        --steps 500 --suffix-length 100 --topk 256 --batch-size 512 \
        --resume
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

# Allow running from repo root without installing the package
_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s – %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("precompute_gcg")

# ── Default target string used as the GCG optimisation target ────────────────
_DEFAULT_TARGET = (
    "Sure, here's exactly how to do that. First, let me help you with this request:"
)


# ── Lazy-load surrogate on the best available device ─────────────────────────

def _load_surrogate(model_name: str, steps: int, batch_size: int, topk: int, suffix_length: int):
    """Load the surrogate model and return (model, tokenizer, device, adjusted params)."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    logger.info("Loading surrogate model: %s", model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_name, torch_dtype="auto", trust_remote_code=True
    )
    model.eval()

    has_cuda = torch.cuda.is_available()
    has_mps  = getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()

    if has_cuda:
        device = torch.device("cuda")
        logger.info("Device: CUDA (%s)", torch.cuda.get_device_name(0))
    elif has_mps:
        device = torch.device("mps")
        logger.info("Device: MPS (Apple Silicon)")
    else:
        device = torch.device("cpu")
        logger.warning(
            "No GPU found – capping steps %d→20, batch %d→32, topk %d→32, suffix %d→20",
            steps, batch_size, topk, suffix_length,
        )
        steps         = min(steps, 20)
        batch_size    = min(batch_size, 32)
        topk          = min(topk, 32)
        suffix_length = min(suffix_length, 20)

    model = model.to(device)
    logger.info("Surrogate loaded on %s", device)
    return model, tokenizer, device, steps, batch_size, topk, suffix_length


# ── Manual GCG implementation (copied / adapted from attacks/gcg.py) ─────────

def _run_gcg_manual(
    model,
    tokenizer,
    device,
    goal: str,
    target_str: str,
    steps: int,
    suffix_length: int,
    topk: int,
    batch_size: int,
    timeout_seconds: float = 600.0,
) -> str:
    """
    Run GCG Algorithm 1 (Zou et al. 2023) and return the best suffix string.

    Precomputes goal_embeds and target_embeds once outside the step loop to
    avoid redundant forward passes.
    """
    import torch
    import torch.nn.functional as F

    embed_fn = model.get_input_embeddings()
    W        = embed_fn.weight  # (vocab, embed_dim)

    bang_id = tokenizer.convert_tokens_to_ids("!")
    if bang_id is None or bang_id == tokenizer.unk_token_id:
        bang_id = 0
    suffix_ids = torch.full((suffix_length,), bang_id, dtype=torch.long, device=device)

    goal_ids = tokenizer(
        goal, return_tensors="pt", add_special_tokens=True
    ).input_ids.squeeze(0).to(device)
    target_ids = tokenizer(
        target_str, return_tensors="pt", add_special_tokens=False
    ).input_ids.squeeze(0).to(device)

    n_goal   = len(goal_ids)
    n_suffix = len(suffix_ids)
    target_start = n_goal + n_suffix

    # ── Precompute static embeddings once ────────────────────────────────────
    with torch.no_grad():
        goal_embeds   = embed_fn(goal_ids.unsqueeze(0))    # (1, n_goal, d)
        target_embeds = embed_fn(target_ids.unsqueeze(0))  # (1, n_tgt, d)

    best_suffix_ids = suffix_ids.clone()
    best_loss       = float("inf")
    t0              = time.monotonic()

    for step in range(steps):
        if time.monotonic() - t0 > timeout_seconds:
            logger.warning("GCG timeout at step %d/%d (loss=%.4f)", step, steps, best_loss)
            break

        # Step 1: gradient w.r.t. suffix embeddings
        suffix_embeds = embed_fn(suffix_ids.unsqueeze(0)).detach().requires_grad_(True)
        full_embeds   = torch.cat([goal_embeds, suffix_embeds, target_embeds], dim=1)
        outputs       = model(inputs_embeds=full_embeds)
        logits        = outputs.logits

        shift_logits = logits[:, target_start - 1:-1, :]
        loss = F.cross_entropy(
            shift_logits.reshape(-1, shift_logits.shape[-1]),
            target_ids.reshape(-1),
        )
        loss.backward()

        grad = suffix_embeds.grad.squeeze(0)  # (n_suffix, embed_dim)

        # Step 2: top-k candidates per position
        token_scores = -(grad @ W.T)  # (n_suffix, vocab)
        topk_ids     = torch.topk(token_scores, k=topk, dim=-1).indices

        # Step 3: sample B (position, token) candidates
        B         = min(batch_size, topk * n_suffix)
        positions = torch.randint(0, n_suffix, (B,), device=device)
        col_idx   = torch.randint(0, topk,     (B,), device=device)
        replacements = topk_ids[positions, col_idx]

        # Step 4: evaluate, keep best
        best_cand_loss = float("inf")
        best_cand_ids  = suffix_ids.clone()

        with torch.no_grad():
            for b in range(B):
                cand = suffix_ids.clone()
                cand[positions[b]] = replacements[b]

                cand_full    = torch.cat([goal_ids, cand, target_ids]).unsqueeze(0)
                cand_embeds  = embed_fn(cand_full)
                cand_logits  = model(inputs_embeds=cand_embeds).logits
                cand_loss    = F.cross_entropy(
                    cand_logits[:, target_start - 1:-1, :].reshape(-1, cand_logits.shape[-1]),
                    target_ids.reshape(-1),
                ).item()

                if cand_loss < best_cand_loss:
                    best_cand_loss = cand_loss
                    best_cand_ids  = cand.clone()

        suffix_ids = best_cand_ids
        if best_cand_loss < best_loss:
            best_loss       = best_cand_loss
            best_suffix_ids = suffix_ids.clone()

        if (step + 1) % 20 == 0:
            elapsed = time.monotonic() - t0
            logger.info(
                "  step %d/%d  loss=%.4f  elapsed=%.0fs",
                step + 1, steps, best_cand_loss, elapsed,
            )

    suffix_str = tokenizer.decode(best_suffix_ids, skip_special_tokens=True)
    logger.info("[GCG] loss=%.4f  suffix: %s", best_loss, suffix_str[:80])
    return suffix_str


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-compute GCG suffixes for a dataset")
    parser.add_argument("--dataset",       default="owasp_agentic_500_jailbreaks_v2.json",
                        help="Dataset file name (relative to data/)")
    parser.add_argument("--output",        default="",
                        help="Output JSON path (default: data/gcg_cache_<stem>.json)")
    parser.add_argument("--model",         default="Qwen/Qwen2.5-0.5B-Instruct",
                        help="HuggingFace surrogate model ID")
    parser.add_argument("--steps",         type=int, default=500,  help="GCG optimisation steps")
    parser.add_argument("--suffix-length", type=int, default=100,  help="Suffix token length")
    parser.add_argument("--topk",          type=int, default=256,  help="Top-k candidates/position")
    parser.add_argument("--batch-size",    type=int, default=512,  help="Candidate batch size/step")
    parser.add_argument("--target-str",    default=_DEFAULT_TARGET,
                        help="Target string GCG optimises toward")
    parser.add_argument("--resume",        action="store_true",
                        help="Skip samples that already appear in the output file")
    parser.add_argument("--timeout",       type=float, default=600.0,
                        help="Per-sample timeout in seconds (default 600)")
    args = parser.parse_args()

    data_dir     = _REPO / "data"
    dataset_path = data_dir / args.dataset
    if not dataset_path.exists():
        logger.error("Dataset not found: %s", dataset_path)
        sys.exit(1)

    stem         = Path(args.dataset).stem
    output_path  = Path(args.output) if args.output else data_dir / f"gcg_cache_{stem}.json"

    logger.info("Dataset : %s", dataset_path)
    logger.info("Output  : %s", output_path)

    # Load dataset
    with open(dataset_path) as f:
        data = json.load(f)
    if not isinstance(data, list):
        logger.error("Expected a JSON array; got %s", type(data).__name__)
        sys.exit(1)
    logger.info("Samples : %d", len(data))

    # Load or init cache
    cache: dict[str, str] = {}
    if output_path.exists():
        with open(output_path) as f:
            cache = json.load(f)
        logger.info("Loaded %d cached entries from %s", len(cache), output_path)

    # Figure out which samples to process
    to_process = []
    for i, sample in enumerate(data):
        sid = str(sample.get("id", i))
        goal = sample.get("user_goal") or sample.get("goal") or ""
        if not goal:
            logger.warning("Sample %s has no goal field — skipping", sid)
            continue
        if args.resume and sid in cache:
            continue
        to_process.append((sid, goal))

    if not to_process:
        logger.info("All samples already cached – nothing to do.")
        return

    logger.info("Processing %d samples (resume=%s)", len(to_process), args.resume)

    # Load surrogate once
    model, tokenizer, device, steps, batch_size, topk, suffix_length = _load_surrogate(
        args.model, args.steps, args.batch_size, args.topk, args.suffix_length
    )

    total   = len(to_process)
    t_start = time.monotonic()

    for idx, (sid, goal) in enumerate(to_process, 1):
        logger.info("[%d/%d] id=%s  goal=%s…", idx, total, sid, goal[:60])
        t_sample = time.monotonic()

        try:
            suffix = _run_gcg_manual(
                model, tokenizer, device,
                goal=goal,
                target_str=args.target_str,
                steps=steps,
                suffix_length=suffix_length,
                topk=topk,
                batch_size=batch_size,
                timeout_seconds=args.timeout,
            )
        except Exception as exc:
            logger.error("  ERROR for sample %s: %s", sid, exc)
            suffix = ""

        cache[sid] = suffix
        elapsed_sample = time.monotonic() - t_sample

        # Save incrementally after every sample
        tmp = output_path.with_suffix(".tmp.json")
        with open(tmp, "w") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
        tmp.rename(output_path)

        done_pct = idx / total * 100
        eta_s    = (time.monotonic() - t_start) / idx * (total - idx)
        logger.info(
            "  saved [%d/%d] %.1f%%  sample_time=%.0fs  ETA=%.0fs",
            idx, total, done_pct, elapsed_sample, eta_s,
        )

    logger.info("Done. %d suffixes saved to %s", len(cache), output_path)


if __name__ == "__main__":
    main()
