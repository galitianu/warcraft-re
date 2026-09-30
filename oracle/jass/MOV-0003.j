// MOV-0003: how does a diagonal move differ from the straight baseline?
// Same distance (1000) and initial facing toward the target as the baseline; axis rotated 45 degrees.
// Custom-text trigger replacing Melee Initialization, with "Run on Map Initialization"
// unchecked. Library oracle-v1 (oracle/jass/lib/oracle-v1.j) is pasted just above.

function MOV0003Hook takes nothing returns nothing
    if OracleCallback() == 0 then
        call OracleOrderPoint("u0", OracleUnit(0), "move", 707.106781, 707.106781)
    endif
endfunction

function MOV0003Start takes nothing returns nothing
    local unit u
    call OracleBegin("MOV-0003", "MOV-0003", 1000)
    set u = CreateUnit(Player(0), 'hfoo', 0, 0, 45)
    call SetUnitAcquireRange(u, 0)
    call SetCameraPosition(384, 192)
    call OracleWatchUnit("u0", u)
    call OracleSetup("u0=hfoo,0,0,45|order_at_callback_0=move,707.106781,707.106781")
    call OracleRun(0.02, 250, function MOV0003Hook)
    set u = null
endfunction

function InitTrig_Melee_Initialization takes nothing returns nothing
    set gg_trg_Melee_Initialization = CreateTrigger()
    call TriggerRegisterTimerEventSingle(gg_trg_Melee_Initialization, 0.5)
    call TriggerAddAction(gg_trg_Melee_Initialization, function MOV0003Start)
endfunction
