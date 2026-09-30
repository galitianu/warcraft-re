// MOV-0006: how do facing and displacement change when a moving unit is redirected by 90 degrees?
// At callback 50 the new target is (x, y + 1000) from that callback's position.
// Custom-text trigger replacing Melee Initialization, with "Run on Map Initialization"
// unchecked. Library oracle-v1 (oracle/jass/lib/oracle-v1.j) is pasted just above.

function MOV0006Hook takes nothing returns nothing
    local unit u = OracleUnit(0)
    if OracleCallback() == 0 then
        call OracleOrderPoint("u0", u, "move", 1000, 0)
    elseif OracleCallback() == 50 then
        call OracleOrderPoint("u0", u, "move", GetUnitX(u), GetUnitY(u) + 1000)
    endif
    set u = null
endfunction

function MOV0006Start takes nothing returns nothing
    local unit u
    call OracleBegin("MOV-0006", "MOV-0006", 1000)
    set u = CreateUnit(Player(0), 'hfoo', 0, 0, 0)
    call SetUnitAcquireRange(u, 0)
    call SetCameraPosition(384, 192)
    call OracleWatchUnit("u0", u)
    call OracleSetup("u0=hfoo,0,0,0|order_at_callback_0=move,1000,0|order_at_callback_50=move,x,y+1000")
    call OracleRun(0.02, 250, function MOV0006Hook)
    set u = null
endfunction

function InitTrig_Melee_Initialization takes nothing returns nothing
    set gg_trg_Melee_Initialization = CreateTrigger()
    call TriggerRegisterTimerEventSingle(gg_trg_Melee_Initialization, 0.5)
    call TriggerAddAction(gg_trg_Melee_Initialization, function MOV0006Start)
endfunction
