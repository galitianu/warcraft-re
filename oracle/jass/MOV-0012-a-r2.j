// MOV-0012 variant a, revision r2: how does near-axial heading noise depend on start position
// modulo 1/64, target position, the Y = 0 frame boundary, distance and travel direction?
// r2: CreateUnit at (0.001953125, 0) placed the unit at exactly (0, 0) in
// MOV-0012-a, so this revision creates it at the origin and sets X/Y explicitly.
// Variant a: start X at 1/512 (frac(64x) = 0.125); target as JASS-0001-p001.
// u0 hfoo created at (0, 0) facing 0, then SetUnitX 0.001953125 / SetUnitY 0; callback 0: move to (1000, 0).
// Requested period 0.001 s, 1000 callbacks. Each callback also reads a 10 s clock
// started in callback 0 and prints X/Y/facing with 9 decimals (STATE event).
// Custom-text trigger replacing Melee Initialization, with "Run on Map Initialization"
// unchecked. Library oracle-v1 (oracle/jass/lib/oracle-v1.j) is pasted just above.
// OracleState parent 3 is owned by this case: 0 = 10 s clock.

function MOV0012Real9 takes real value returns string
    return R2SW(value, 1, 9)
endfunction

function MOV0012Hook takes nothing returns nothing
    local unit u = OracleUnit(0)
    local timer c10
    if OracleCallback() == 0 then
        set c10 = CreateTimer()
        call TimerStart(c10, 10, false, null)
        call SaveTimerHandle(udg_OracleState, 3, 0, c10)
        call OracleOrderPoint("u0", u, "move", 1000, 0)
    else
        set c10 = LoadTimerHandle(udg_OracleState, 3, 0)
    endif
    call OracleEvent("STATE|c10_9=" + MOV0012Real9(TimerGetElapsed(c10)) + "|x_9=" + MOV0012Real9(GetUnitX(u)) + "|y_9=" + MOV0012Real9(GetUnitY(u)) + "|facing_9=" + MOV0012Real9(GetUnitFacing(u)))
    set u = null
    set c10 = null
endfunction

function MOV0012Start takes nothing returns nothing
    local unit u
    call OracleBegin("MOV-0012", "MOV-0012-a-r2", 1000)
    set u = CreateUnit(Player(0), 'hfoo', 0, 0, 0)
    call SetUnitX(u, 0.001953125)
    call SetUnitY(u, 0)
    call SetUnitAcquireRange(u, 0)
    call SetCameraPosition(384, 192)
    call OracleWatchUnit("u0", u)
    call OracleSetup("u0=hfoo,0,0,0|set_xy=0.001953125,0|order_at_callback_0=move,1000,0|aux_clock=10|variant=a")
    call OracleRun(0.001, 1000, function MOV0012Hook)
    set u = null
endfunction

function InitTrig_Melee_Initialization takes nothing returns nothing
    set gg_trg_Melee_Initialization = CreateTrigger()
    call TriggerRegisterTimerEventSingle(gg_trg_Melee_Initialization, 0.5)
    call TriggerAddAction(gg_trg_Melee_Initialization, function MOV0012Start)
endfunction
