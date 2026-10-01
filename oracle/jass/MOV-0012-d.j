// MOV-0012 variant d: how does near-axial heading noise depend on start position
// modulo 1/64, target position, the Y = 0 frame boundary, distance and travel direction?
// Variant d: east travel along Y = 256, away from the Y = 0 frame boundary.
// u0 hfoo at (0, 256) facing 0; callback 0: move to (1000, 256).
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
        call OracleOrderPoint("u0", u, "move", 1000, 256)
    else
        set c10 = LoadTimerHandle(udg_OracleState, 3, 0)
    endif
    call OracleEvent("STATE|c10_9=" + MOV0012Real9(TimerGetElapsed(c10)) + "|x_9=" + MOV0012Real9(GetUnitX(u)) + "|y_9=" + MOV0012Real9(GetUnitY(u)) + "|facing_9=" + MOV0012Real9(GetUnitFacing(u)))
    set u = null
    set c10 = null
endfunction

function MOV0012Start takes nothing returns nothing
    local unit u
    call OracleBegin("MOV-0012", "MOV-0012-d", 1000)
    set u = CreateUnit(Player(0), 'hfoo', 0, 256, 0)
    call SetUnitAcquireRange(u, 0)
    call SetCameraPosition(384, 192)
    call OracleWatchUnit("u0", u)
    call OracleSetup("u0=hfoo,0,256,0|order_at_callback_0=move,1000,256|aux_clock=10|variant=d")
    call OracleRun(0.001, 1000, function MOV0012Hook)
    set u = null
endfunction

function InitTrig_Melee_Initialization takes nothing returns nothing
    set gg_trg_Melee_Initialization = CreateTrigger()
    call TriggerRegisterTimerEventSingle(gg_trg_Melee_Initialization, 0.5)
    call TriggerAddAction(gg_trg_Melee_Initialization, function MOV0012Start)
endfunction
