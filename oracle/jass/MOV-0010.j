// MOV-0010: what happens to position, facing and order after a moving unit receives stop?
// Custom-text trigger replacing Melee Initialization, with "Run on Map Initialization"
// unchecked. Library oracle-v1 (oracle/jass/lib/oracle-v1.j) is pasted just above.

function MOV0010Hook takes nothing returns nothing
    if OracleCallback() == 0 then
        call OracleOrderPoint("u0", OracleUnit(0), "move", 1000, 0)
    elseif OracleCallback() == 50 then
        call OracleOrderImmediate("u0", OracleUnit(0), "stop")
    endif
endfunction

function MOV0010Start takes nothing returns nothing
    local unit u
    call OracleBegin("MOV-0010", "MOV-0010", 1000)
    set u = CreateUnit(Player(0), 'hfoo', 0, 0, 0)
    call SetUnitAcquireRange(u, 0)
    call SetCameraPosition(384, 192)
    call OracleWatchUnit("u0", u)
    call OracleSetup("u0=hfoo,0,0,0|order_at_callback_0=move,1000,0|order_at_callback_50=stop")
    call OracleRun(0.02, 250, function MOV0010Hook)
    set u = null
endfunction

function InitTrig_Melee_Initialization takes nothing returns nothing
    set gg_trg_Melee_Initialization = CreateTrigger()
    call TriggerRegisterTimerEventSingle(gg_trg_Melee_Initialization, 0.5)
    call TriggerAddAction(gg_trg_Melee_Initialization, function MOV0010Start)
endfunction
