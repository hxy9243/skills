tags

[Operating Systems](https://braindump.jethro.dev/posts/operating_systems)

## Pipelining

- Increases throughput, but not latency

### Structural Hazard

### Data Hazard

- Resolved with extra hardware

### Control Hazard

- Branch instructions need to tell which branch, but have only just read from memory
- Branch prediction (static/dynamic)

## Pipelined Datapath and Control

### Issues

1. Write-back stage places the result back into the register file in the middle of the data path (Data Hazard)
2. Selection of the next value of the PC, between incremented PC and branch address from the MEM stage (Control Hazard)

Data flow does not affect current instruction, but only influence later instructions.
