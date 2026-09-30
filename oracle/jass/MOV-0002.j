// Hand-authored World Editor custom-text trigger, replacing Melee Initialization.
// Requires one GUI variable: OracleState, type Hashtable, not an array, initial None.
// Requested callback period is 0.02 seconds; it is NOT a claimed simulation tick.

function OracleMOV0002Real takes real value returns string
    return R2SW(value, 1, 6)
endfunction

function OracleMOV0002Log takes string record returns nothing
    local integer seq = LoadInteger(udg_OracleState, 0, 3)
    call Preload("@O|" + I2S(seq) + "|" + record)
    call SaveInteger(udg_OracleState, 0, 3, seq + 1)
endfunction

function OracleMOV0002Unit takes string name, unit u, real elapsed returns nothing
    call OracleMOV0002Log("SAMPLE|" + OracleMOV0002Real(elapsed) + "|" + name + "|" + OracleMOV0002Real(GetUnitX(u)) + "|" + OracleMOV0002Real(GetUnitY(u)) + "|" + OracleMOV0002Real(GetUnitFacing(u)) + "|" + I2S(GetUnitCurrentOrder(u)))
endfunction

function OracleMOV0002Sample takes nothing returns nothing
    local timer clock = LoadTimerHandle(udg_OracleState, 0, 2)
    local real elapsed = TimerGetElapsed(clock)
    call OracleMOV0002Unit("u0", LoadUnitHandle(udg_OracleState, 0, 0), elapsed)
    call OracleMOV0002Unit("u1", LoadUnitHandle(udg_OracleState, 0, 1), elapsed)
    set clock = null
endfunction

function OracleMOV0002Tick takes nothing returns nothing
    local integer count = LoadInteger(udg_OracleState, 0, 4) + 1
    call SaveInteger(udg_OracleState, 0, 4, count)
    call OracleMOV0002Sample()
    if count == 250 then
        call PauseTimer(GetExpiredTimer())
        call OracleMOV0002Log("END|MOV-0002|callbacks=250")
        call PreloadGenEnd("MOV-0002.txt")
        call DisplayTimedTextToPlayer(Player(0), 0, 0, 60, "MOV-0002 complete: MOV-0002.txt written")
    endif
endfunction

function OracleMOV0002Start takes nothing returns nothing
    local unit moving
    local unit control
    local timer clock = CreateTimer()
    local timer sampler = CreateTimer()
    local boolean accepted
    set udg_OracleState = InitHashtable()
    call SetGameSpeed(MAP_SPEED_NORMAL)
    call SetMapFlag(MAP_LOCK_SPEED, true)
    call SetTimeOfDay(12)
    call SuspendTimeOfDay(true)
    call FogEnable(false)
    call FogMaskEnable(false)
    set moving = CreateUnit(Player(0), 'hfoo', 0, 0, 0)
    set control = CreateUnit(Player(0), 'hfoo', 0, 384, 0)
    call SetUnitAcquireRange(moving, 0)
    call SetUnitAcquireRange(control, 0)
    call SaveUnitHandle(udg_OracleState, 0, 0, moving)
    call SaveUnitHandle(udg_OracleState, 0, 1, control)
    call SaveTimerHandle(udg_OracleState, 0, 2, clock)
    call SetCameraPosition(384, 192)
    call PreloadGenClear()
    call PreloadGenStart()
    call OracleMOV0002Log("BEGIN|MOV-0002|wc3-1.29.2-9231-x86|time_unit=seconds|numeric_format=R2SW_6")
    call OracleMOV0002Log("SETUP|u0=hfoo,0,0,0|u1=hfoo,0,384,0|target=1000,0|requested_period=0.02|intervals=250|speed=" + OracleMOV0002Real(GetUnitMoveSpeed(moving)))
    call TimerStart(clock, 1000, false, null)
    call OracleMOV0002Sample()
    set accepted = IssuePointOrder(moving, "move", 1000, 0)
    if accepted then
        call OracleMOV0002Log("ACTION|" + OracleMOV0002Real(TimerGetElapsed(clock)) + "|u0|move|1000|0|accepted=1")
    else
        call OracleMOV0002Log("ACTION|" + OracleMOV0002Real(TimerGetElapsed(clock)) + "|u0|move|1000|0|accepted=0")
    endif
    call TimerStart(sampler, 0.02, true, function OracleMOV0002Tick)
    set moving = null
    set control = null
    set clock = null
    set sampler = null
endfunction

function InitTrig_Melee_Initialization takes nothing returns nothing
    set gg_trg_Melee_Initialization = CreateTrigger()
    call TriggerRegisterTimerEventSingle(gg_trg_Melee_Initialization, 0.5)
    call TriggerAddAction(gg_trg_Melee_Initialization, function OracleMOV0002Start)
endfunction
