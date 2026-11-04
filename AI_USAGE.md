# AI / Coding-Assistant Usage

## Tools & Scope

OpenAI ChatGPT/Codex was used to explain the assignment and code, develop/refactor independent client delivery and semantic overload handling, investigate timing/performance, add regression tests, orchestrate the unchanged school workloads, organize result files and draft setup/report documentation. The assistant used local files, Python/Node test tools, SSH into the team's Ubuntu VM and browser automation for validation.

## Useful Suggestion & Verification

Independent client sender tasks prevent one blocked socket from holding up publication to healthy clients. Shared final history with a per-client bookmark avoids copying a final backlog into every provisional queue. The group’s selected benchmark evidence is retained under `results/stage5/` and `results/stage6/`.

## Generated Suggestion/Code that Required Modification

**Initial Suggestion:** Send a ping after every caption and wait for the client's pong before sending the next caption. This helps detect slow connections.

**Issue:** Waiting after every caption slows delivery when the connection takes longer to reply, even if the client can keep up. For example, a 200 ms ping/pong wait limits the sender to about five captions per second.

**Change:** Send a small group of captions before checking ping/pong. The group size adapts to the connection delay and caption arrival rate, up to eight messages. A byte threshold can trigger an earlier check. This reduces waiting while keeping checks for slow connections.

## Limitations & Responsibility

Generated claims are not evidence on their own. Experimental results come from the saved raw files. Random packet loss and hidden workloads prevent a promise of a particular grade or universal 100% completeness. The conservative post-congestion cooldown remains a trade-off described in the report. Each team member must understand the code they claim, review the final declarations/results and be able to explain or modify the implementation during the viva.
