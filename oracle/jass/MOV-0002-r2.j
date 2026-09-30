// MOV-0002 revision r2: Phase 0's straight-move setup (MOV-0002.j) rebuilt on oracle-v1.
// Same units, target, period, callback count and clock; only instrumentation changed.
// Custom-text trigger replacing Melee Initialization, with "Run on Map Initialization"
// unchecked. Library oracle-v1 (oracle/jass/lib/oracle-v1.j) is pasted just above.

function MOV0002R2Hook takes nothing returns nothing
    if OracleCallback() == 0 then
        call OracleOrderPoint("u0", OracleUnit(0), "move", 1000, 0)
    endif
endfunction

function MOV0002R2Start takes nothing returns nothing
    local unit moving
    local unit control
    call OracleBegin("MOV-0002", "MOV-0002-r2", 1000)
    set moving = CreateUnit(Player(0), 'hfoo', 0, 0, 0)
    set control = CreateUnit(Player(0), 'hfoo', 0, 384, 0)
    call SetUnitAcquireRange(moving, 0)
    call SetUnitAcquireRange(control, 0)
    call SetCameraPosition(384, 192)
    call OracleWatchUnit("u0", moving)
    call OracleWatchUnit("u1", control)
    call OracleSetup("u0=hfoo,0,0,0|u1=hfoo,0,384,0|u0_order_at_callback_0=move,1000,0")
    call OracleRun(0.02, 250, function MOV0002R2Hook)
    set moving = null
    set control = null
endfunction

function InitTrig_Melee_Initialization takes nothing returns nothing
    set gg_trg_Melee_Initialization = CreateTrigger()
    call TriggerRegisterTimerEventSingle(gg_trg_Melee_Initialization, 0.5)
    call TriggerAddAction(gg_trg_Melee_Initialization, function MOV0002R2Start)
endfunction
