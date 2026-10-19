globals
 hashtable udg_OracleState = null
 trigger gg_trg_Melee_Initialization = null
endglobals
// Oracle shared instrumentation, library oracle-v1 (Phase 1).
// Paste this file unchanged at the top of the map's single custom-text trigger
// (Melee Initialization), immediately followed by one case file. Keep the map
// header empty: World Editor 1.29 marks a map with header custom script as
// requiring the expansion, which would change the map type from Phase 0's.
// Requires one GUI variable: OracleState, type Hashtable, not an array, initial None.
// Each case trigger creates its own setup; this library only observes and logs.
// Output: one "@O|sequence|KIND|..." string per Preload call, written by
// PreloadGenEnd to CustomMapData\<map label>.txt.
// Requested periods are sampling requests, NOT claimed simulation ticks.
//
// OracleState parent 0: 0 next sequence, 1 clock, 2 test id, 3 map label,
// 4 watched count, 5 callback count, 6 requested callbacks, 7 hook trigger,
// 8 sampler timer, 9 clock duration. Parent 1: watched units. Parent 2: names.

function OracleReal takes real value returns string
    return R2SW(value, 1, 6)
endfunction

function OracleLog takes string record returns nothing
    local integer seq = LoadInteger(udg_OracleState, 0, 0)
    call Preload("@O|" + I2S(seq) + "|" + record)
    call SaveInteger(udg_OracleState, 0, 0, seq + 1)
endfunction

function OracleNow takes nothing returns real
    return TimerGetElapsed(LoadTimerHandle(udg_OracleState, 0, 1))
endfunction

function OracleCallback takes nothing returns integer
    return LoadInteger(udg_OracleState, 0, 5)
endfunction

function OracleUnit takes integer index returns unit
    return LoadUnitHandle(udg_OracleState, 1, index)
endfunction

function OracleBegin takes string testId, string mapLabel, real clockDuration returns nothing
    set udg_OracleState = InitHashtable()
    call SaveStr(udg_OracleState, 0, 2, testId)
    call SaveStr(udg_OracleState, 0, 3, mapLabel)
    call SaveReal(udg_OracleState, 0, 9, clockDuration)
    call SetGameSpeed(MAP_SPEED_NORMAL)
    call SetMapFlag(MAP_LOCK_SPEED, true)
    call SetTimeOfDay(12)
    call SuspendTimeOfDay(true)
    call FogEnable(false)
    call FogMaskEnable(false)
    call PreloadGenClear()
    call PreloadGenStart()
    call OracleLog("BEGIN|" + testId + "|wc3-1.29.2-9231-x86|map=" + mapLabel + "|lib=oracle-v1|time_unit=seconds|numeric_format=R2SW_6|clock_duration=" + OracleReal(clockDuration))
endfunction

function OracleSetup takes string record returns nothing
    call OracleLog("SETUP|" + record)
endfunction

function OracleWatchUnit takes string name, unit u returns nothing
    local integer n = LoadInteger(udg_OracleState, 0, 4)
    call SaveUnitHandle(udg_OracleState, 1, n, u)
    call SaveStr(udg_OracleState, 2, n, name)
    call SaveInteger(udg_OracleState, 0, 4, n + 1)
    call OracleLog("WATCH|" + name + "|type=" + UnitId2String(GetUnitTypeId(u)) + "|speed=" + OracleReal(GetUnitMoveSpeed(u)) + "|default_speed=" + OracleReal(GetUnitDefaultMoveSpeed(u)))
endfunction

function OracleSampleAt takes real elapsed returns nothing
    local integer i = 0
    local integer n = LoadInteger(udg_OracleState, 0, 4)
    local unit u
    loop
        exitwhen i >= n
        set u = LoadUnitHandle(udg_OracleState, 1, i)
        call OracleLog("SAMPLE|" + OracleReal(elapsed) + "|" + LoadStr(udg_OracleState, 2, i) + "|" + OracleReal(GetUnitX(u)) + "|" + OracleReal(GetUnitY(u)) + "|" + OracleReal(GetUnitFacing(u)) + "|" + I2S(GetUnitCurrentOrder(u)))
        set i = i + 1
    endloop
    set u = null
endfunction

function OracleEvent takes string record returns nothing
    call OracleLog("EVENT|" + OracleReal(OracleNow()) + "|" + record)
endfunction

function OracleAccepted takes boolean accepted returns string
    if accepted then
        return "accepted=1"
    endif
    return "accepted=0"
endfunction

function OracleOrderPoint takes string name, unit u, string order, real x, real y returns boolean
    local boolean accepted = IssuePointOrder(u, order, x, y)
    call OracleLog("ACTION|" + OracleReal(OracleNow()) + "|" + name + "|" + order + "|" + OracleReal(x) + "|" + OracleReal(y) + "|" + OracleAccepted(accepted))
    return accepted
endfunction

function OracleOrderImmediate takes string name, unit u, string order returns boolean
    local boolean accepted = IssueImmediateOrder(u, order)
    call OracleLog("ACTION|" + OracleReal(OracleNow()) + "|" + name + "|" + order + "|" + OracleAccepted(accepted))
    return accepted
endfunction

function OracleEnd takes nothing returns nothing
    local string label = LoadStr(udg_OracleState, 0, 3)
    call OracleLog("END|" + LoadStr(udg_OracleState, 0, 2) + "|map=" + label + "|callbacks=" + I2S(OracleCallback()))
    call PreloadGenEnd(label + ".txt")
    call DisplayTimedTextToPlayer(Player(0), 0, 0, 60, label + " complete: " + label + ".txt written")
endfunction

// One sampler callback: TICK, one SAMPLE per watched unit, then the case hook.
// All records of a callback share one elapsed-clock reading.
function OracleTick takes nothing returns nothing
    local integer count = OracleCallback() + 1
    local real elapsed = OracleNow()
    call SaveInteger(udg_OracleState, 0, 5, count)
    call OracleLog("TICK|" + OracleReal(elapsed) + "|" + I2S(count))
    call OracleSampleAt(elapsed)
    call TriggerExecute(LoadTriggerHandle(udg_OracleState, 0, 7))
    if count == LoadInteger(udg_OracleState, 0, 6) then
        call PauseTimer(GetExpiredTimer())
        call OracleEnd()
    endif
endfunction

// Starts the elapsed clock (time zero), takes callback 0's initial samples,
// runs the hook for callback 0, then requests periodic sampler callbacks.
// The hook reads OracleCallback() to decide the case's actions.
function OracleRun takes real period, integer callbacks, code hook returns nothing
    local timer clock = CreateTimer()
    local timer sampler = CreateTimer()
    local trigger t = CreateTrigger()
    local real elapsed
    call TriggerAddAction(t, hook)
    call SaveTriggerHandle(udg_OracleState, 0, 7, t)
    call SaveInteger(udg_OracleState, 0, 6, callbacks)
    call SaveTimerHandle(udg_OracleState, 0, 1, clock)
    call SaveTimerHandle(udg_OracleState, 0, 8, sampler)
    call OracleLog("RUN|requested_period=" + OracleReal(period) + "|callbacks=" + I2S(callbacks))
    call TimerStart(clock, LoadReal(udg_OracleState, 0, 9), false, null)
    set elapsed = OracleNow()
    call OracleLog("TICK|" + OracleReal(elapsed) + "|0")
    call OracleSampleAt(elapsed)
    call TriggerExecute(t)
    call TimerStart(sampler, period, true, function OracleTick)
    set clock = null
    set sampler = null
    set t = null
endfunction

// template_sha256=bb67f103cc5c17507fcf63f4928799939f7875538e8ced6b9512b525c8d23efd
// Generated by oracle_codegen v1; do not edit.
// scenario_sha256=e7e3bf12f250c8a9344a21123d3e7328e463b25004556362f96a86416db2e94e
// Packaging revision: MOV-0026-d; library: oracle-v1.

function GeneratedHook takes nothing returns nothing
    if OracleCallback() == 0 then
        call OracleOrderPoint("u0", OracleUnit(0), "move", 16, 16)
        call OracleOrderPoint("u1", OracleUnit(1), "move", 16, 16)
    elseif OracleCallback() == 96 then
        call OracleOrderImmediate("u0", OracleUnit(0), "stop")
    endif
endfunction

function GeneratedStart takes nothing returns nothing
    local unit unit0
    local unit unit1
    call OracleBegin("MOV-0026", "MOV-0026-d", 1000)
    set unit0 = CreateUnit(Player(0), 'hfoo', -484, 16, 0)
    set unit1 = CreateUnit(Player(0), 'hfoo', 516, 16, 180)
    call SetUnitAcquireRange(unit0, 0)
    call SetUnitAcquireRange(unit1, 0)
    call SetCameraPosition(384, 192)
    call OracleWatchUnit("u0", unit0)
    call OracleWatchUnit("u1", unit1)
    call OracleSetup("scenario_sha256=e7e3bf12f250c8a9344a21123d3e7328e463b25004556362f96a86416db2e94e|scenario_version=1|u0=hfoo,-484,16,0|u1=hfoo,516,16,180|action0=0,u0,move,target,16,16|action1=0,u1,move,target,16,16|action2=96,u0,stop")
    call OracleRun(0.02, 600, function GeneratedHook)
    set unit0 = null
    set unit1 = null
endfunction

function InitTrig_Melee_Initialization takes nothing returns nothing
    set gg_trg_Melee_Initialization = CreateTrigger()
    call TriggerRegisterTimerEventSingle(gg_trg_Melee_Initialization, 0.5)
    call TriggerAddAction(gg_trg_Melee_Initialization, function GeneratedStart)
endfunction
