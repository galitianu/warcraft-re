// MOV-0007: how do facing and displacement change when a moving unit is redirected by 180 degrees?
// At callback 50 the new target is (x - 1000, y) from that callback's position.
// Custom-text trigger replacing Melee Initialization, with "Run on Map Initialization"
// unchecked. Library oracle-v1 (oracle/jass/lib/oracle-v1.j) is pasted just above.

function MOV0007Hook takes nothing returns nothing
    local unit u = OracleUnit(0)
    if OracleCallback() == 0 then
        call OracleOrderPoint("u0", u, "move", 1000, 0)
    elseif OracleCallback() == 50 then
        call OracleOrderPoint("u0", u, "move", GetUnitX(u) - 1000, GetUnitY(u))
    endif
    set u = null
endfunction

function MOV0007Start takes nothing returns nothing
    local unit u
    call OracleBegin("MOV-0007", "MOV-0007", 1000)
    set u = CreateUnit(Player(0), 'hfoo', 0, 0, 0)
    call SetUnitAcquireRange(u, 0)
    call SetCameraPosition(384, 192)
    call OracleWatchUnit("u0", u)
    call OracleSetup("u0=hfoo,0,0,0|order_at_callback_0=move,1000,0|order_at_callback_50=move,x-1000,y")
    call OracleRun(0.02, 250, function MOV0007Hook)
    set u = null
endfunction

function InitTrig_Melee_Initialization takes nothing returns nothing
    set gg_trg_Melee_Initialization = CreateTrigger()
    call TriggerRegisterTimerEventSingle(gg_trg_Melee_Initialization, 0.5)
    call TriggerAddAction(gg_trg_Melee_Initialization, function MOV0007Start)
endfunction
