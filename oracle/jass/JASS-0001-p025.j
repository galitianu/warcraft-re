// JASS-0001 variant p025: how do the requested sampling period and elapsed-time clock
// precision affect recoverable movement observations? Requested period 0.025 s, 200 callbacks.
// Setup is MOV-0002's u0 without the u1 control: one Footman moving to (1000, 0).
// Each callback also reads two auxiliary clocks (100 s, 10 s) started in callback 0,
// the same callback that starts the library's 1000 s clock, and prints selected
// reals with 9 decimals.
// Custom-text trigger replacing Melee Initialization, with "Run on Map Initialization"
// unchecked. Library oracle-v1 (oracle/jass/lib/oracle-v1.j) is pasted just above.
// OracleState parent 3 is owned by this case: 0 = 100 s clock, 1 = 10 s clock.

function JASS0001Real9 takes real value returns string
    return R2SW(value, 1, 9)
endfunction

function JASS0001Hook takes nothing returns nothing
    local unit u = OracleUnit(0)
    local timer c1000 = LoadTimerHandle(udg_OracleState, 0, 1)
    local timer c100
    local timer c10
    if OracleCallback() == 0 then
        set c100 = CreateTimer()
        set c10 = CreateTimer()
        call TimerStart(c100, 100, false, null)
        call TimerStart(c10, 10, false, null)
        call SaveTimerHandle(udg_OracleState, 3, 0, c100)
        call SaveTimerHandle(udg_OracleState, 3, 1, c10)
        call OracleOrderPoint("u0", u, "move", 1000, 0)
    else
        set c100 = LoadTimerHandle(udg_OracleState, 3, 0)
        set c10 = LoadTimerHandle(udg_OracleState, 3, 1)
    endif
    call OracleEvent("CLOCKS|c1000_9=" + JASS0001Real9(TimerGetElapsed(c1000)) + "|c100=" + OracleReal(TimerGetElapsed(c100)) + "|c100_9=" + JASS0001Real9(TimerGetElapsed(c100)) + "|c10=" + OracleReal(TimerGetElapsed(c10)) + "|c10_9=" + JASS0001Real9(TimerGetElapsed(c10)) + "|c10_remaining_9=" + JASS0001Real9(TimerGetRemaining(c10)) + "|x_9=" + JASS0001Real9(GetUnitX(u)) + "|y_9=" + JASS0001Real9(GetUnitY(u)) + "|facing_9=" + JASS0001Real9(GetUnitFacing(u)))
    set u = null
    set c1000 = null
    set c100 = null
    set c10 = null
endfunction

function JASS0001Start takes nothing returns nothing
    local unit u
    call OracleBegin("JASS-0001", "JASS-0001-p025", 1000)
    set u = CreateUnit(Player(0), 'hfoo', 0, 0, 0)
    call SetUnitAcquireRange(u, 0)
    call SetCameraPosition(384, 192)
    call OracleWatchUnit("u0", u)
    call OracleSetup("u0=hfoo,0,0,0|order_at_callback_0=move,1000,0|aux_clocks=100,10|variant=p025")
    call OracleRun(0.025, 200, function JASS0001Hook)
    set u = null
endfunction

function InitTrig_Melee_Initialization takes nothing returns nothing
    set gg_trg_Melee_Initialization = CreateTrigger()
    call TriggerRegisterTimerEventSingle(gg_trg_Melee_Initialization, 0.5)
    call TriggerAddAction(gg_trg_Melee_Initialization, function JASS0001Start)
endfunction
