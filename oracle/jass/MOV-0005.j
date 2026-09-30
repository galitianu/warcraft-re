// MOV-0005: what movement trace and reported speed result when speed is set to 522?
// Custom-text trigger replacing Melee Initialization, with "Run on Map Initialization"
// unchecked. Library oracle-v1 (oracle/jass/lib/oracle-v1.j) is pasted just above.

function MOV0005Hook takes nothing returns nothing
    if OracleCallback() == 0 then
        call OracleOrderPoint("u0", OracleUnit(0), "move", 1000, 0)
    endif
endfunction

function MOV0005Start takes nothing returns nothing
    local unit u
    call OracleBegin("MOV-0005", "MOV-0005", 1000)
    set u = CreateUnit(Player(0), 'hfoo', 0, 0, 0)
    call SetUnitAcquireRange(u, 0)
    call SetUnitMoveSpeed(u, 522)
    call SetCameraPosition(384, 192)
    call OracleWatchUnit("u0", u)
    call OracleSetup("u0=hfoo,0,0,0|set_move_speed=522|order_at_callback_0=move,1000,0")
    call OracleRun(0.02, 250, function MOV0005Hook)
    set u = null
endfunction

function InitTrig_Melee_Initialization takes nothing returns nothing
    set gg_trg_Melee_Initialization = CreateTrigger()
    call TriggerRegisterTimerEventSingle(gg_trg_Melee_Initialization, 0.5)
    call TriggerAddAction(gg_trg_Melee_Initialization, function MOV0005Start)
endfunction
