import XCTest
@testable import VoiceFlowApp

final class HotkeyStateMachineTests: XCTestCase {

    private func makeSM(cooldown: TimeInterval = 0.3) -> HotkeyStateMachine {
        HotkeyStateMachine(cooldown: cooldown)
    }

    private func t(_ offset: TimeInterval) -> Date {
        Date(timeIntervalSinceReferenceDate: 1_000_000 + offset)
    }

    // MARK: - Push-to-talk basics

    func test_fnDown_starts() {
        var sm = makeSM()
        var started = false
        sm.onStart = { started = true }

        sm.fnDown(at: t(0))

        XCTAssertTrue(sm.isRecording)
        XCTAssertTrue(started)
    }

    func test_fnUp_stops() {
        var sm = makeSM()
        var stopped = false
        sm.onStop = { stopped = true }

        sm.fnDown(at: t(0))
        sm.fnUp(at: t(1.0))

        XCTAssertFalse(sm.isRecording)
        XCTAssertTrue(stopped)
    }

    func test_holdAndRelease_fullCycle() {
        var sm = makeSM()
        var starts = 0, stops = 0
        sm.onStart = { starts += 1 }
        sm.onStop  = { stops  += 1 }

        sm.fnDown(at: t(0))    // START
        sm.fnUp(at: t(2.0))    // STOP
        sm.fnDown(at: t(3.0))  // START again (past cooldown)
        sm.fnUp(at: t(5.0))    // STOP again

        XCTAssertFalse(sm.isRecording)
        XCTAssertEqual(starts, 2)
        XCTAssertEqual(stops, 2)
    }

    // MARK: - Burst protection (macOS fires spurious DOWN while held)

    func test_spuriousDown_whileRecording_ignored() {
        var sm = makeSM()
        var starts = 0
        sm.onStart = { starts += 1 }

        sm.fnDown(at: t(0))    // START
        sm.fnDown(at: t(0.1))  // spurious burst — ignored (already recording)
        sm.fnDown(at: t(0.5))  // spurious burst — ignored

        XCTAssertTrue(sm.isRecording)
        XCTAssertEqual(starts, 1)
    }

    func test_fnUp_whileNotRecording_ignored() {
        var sm = makeSM()
        var stopped = false
        sm.onStop = { stopped = true }

        sm.fnUp(at: t(0))  // no-op

        XCTAssertFalse(sm.isRecording)
        XCTAssertFalse(stopped)
    }

    // MARK: - Cooldown after stop

    func test_immediateRestart_blocked_byCooldown() {
        var sm = makeSM(cooldown: 0.3)
        var starts = 0
        sm.onStart = { starts += 1 }

        sm.fnDown(at: t(0))
        sm.fnUp(at: t(1.0))    // stop, lastStopAt = t(1.0)
        sm.fnDown(at: t(1.1))  // 100ms after stop — cooldown → blocked

        XCTAssertFalse(sm.isRecording)
        XCTAssertEqual(starts, 1)
    }

    func test_restartAfterCooldown_allowed() {
        var sm = makeSM(cooldown: 0.3)

        sm.fnDown(at: t(0))
        sm.fnUp(at: t(1.0))
        sm.fnDown(at: t(1.35))  // 0.35s after stop — past cooldown → START

        XCTAssertTrue(sm.isRecording)
    }

    func test_exactCooldownBoundary_blocked() {
        var sm = makeSM(cooldown: 0.3)

        sm.fnDown(at: t(0))
        sm.fnUp(at: t(1.0))
        sm.fnDown(at: t(1.3))  // exactly 0.3s — strict < → blocked

        XCTAssertFalse(sm.isRecording)
    }

    // MARK: - isProcessing blocks fnDown

    func test_fnDown_blockedDuringProcessing() {
        var sm = makeSM()
        var starts = 0
        sm.onStart = { starts += 1 }

        sm.fnDown(at: t(0))
        sm.fnUp(at: t(1.0))
        sm.setProcessing(true)

        sm.fnDown(at: t(2.0))  // past cooldown, but processing → blocked

        XCTAssertFalse(sm.isRecording)
        XCTAssertEqual(starts, 1)
    }

    func test_fnDown_allowedAfterProcessingDone() {
        var sm = makeSM()
        var starts = 0
        sm.onStart = { starts += 1 }

        sm.fnDown(at: t(0))
        sm.fnUp(at: t(1.0))
        sm.setProcessing(true)
        sm.setProcessing(false)  // processing done — sets lastStopAt

        sm.fnDown(at: t(5.0))   // well past cooldown → allowed

        XCTAssertTrue(sm.isRecording)
        XCTAssertEqual(starts, 2)
    }

    func test_setProcessing_false_setsCooldown() {
        var sm = makeSM(cooldown: 0.3)

        sm.fnDown(at: t(0))
        sm.fnUp(at: t(1.0))
        sm.setProcessing(true)
        sm.setProcessing(false)     // lastStopAt = now (somewhere around t(1.0) in real time)

        // Immediate fnDown after processing done — should be blocked by cooldown
        // (setProcessing(false) sets lastStopAt = Date(), not a test date, but
        //  the point is that cooldown resets on processing end)
        XCTAssertFalse(sm.isProcessing)
    }

    func test_reset_clearsProcessing() {
        var sm = makeSM()
        sm.setProcessing(true)
        sm.reset()

        XCTAssertFalse(sm.isProcessing)
    }

    // MARK: - reset

    func test_reset_clearsState() {
        var sm = makeSM()
        sm.fnDown(at: t(0))

        sm.reset()

        XCTAssertFalse(sm.isRecording)
    }

    func test_reset_setsCooldown_blocksImmediateStart() {
        var sm = makeSM(cooldown: 0.3)
        sm.reset()
        sm.fnDown(at: t(0))  // reset sets lastStopAt = now → cooldown active

        XCTAssertFalse(sm.isRecording)
    }

    // MARK: - sync does NOT block subsequent fnDown (the locking bug)

    func test_afterSyncReset_fnDown_startsAgain() {
        // Regression: sync() used to set isRecording=false but isFnPressed stayed true,
        // causing the next fnDown to be skipped. Verify SM itself allows restart after sync.
        var sm = makeSM()
        var starts = 0
        sm.onStart = { starts += 1 }

        sm.fnDown(at: t(0))                          // START
        sm.sync(tcaIsRecording: false, at: t(3.0))   // sync overrides after 2s grace
        XCTAssertFalse(sm.isRecording)               // sync took effect

        sm.fnDown(at: t(3.5))                        // new press — must work
        XCTAssertTrue(sm.isRecording)
        XCTAssertEqual(starts, 2)
    }

    func test_sync_blockedWithin_startedAt_grace() {
        // sync() must be blocked for 2s after fnDown to give TCA time to process
        var sm = makeSM()
        sm.fnDown(at: t(0))

        sm.sync(tcaIsRecording: false, at: t(1.5))   // 1.5s — within 2s grace

        XCTAssertTrue(sm.isRecording)                // not overridden
    }

    // MARK: - sync (TCA drift correction)

    func test_sync_fixesStuckTrue_afterGrace() {
        var sm = makeSM()
        sm.fnDown(at: t(0))

        sm.sync(tcaIsRecording: false, at: t(2.0))

        XCTAssertFalse(sm.isRecording)
    }

    func test_sync_ignoredWithinStopGrace() {
        var sm = makeSM(cooldown: 0.0)
        sm.fnDown(at: t(0))
        sm.fnUp(at: t(0.5))  // stop, lastStopAt = t(0.5)

        sm.sync(tcaIsRecording: true, at: t(0.7))  // 0.2s after stop — within grace

        XCTAssertFalse(sm.isRecording)
    }

    func test_sync_noOp_whenAlreadyInSync() {
        var sm = makeSM()
        sm.sync(tcaIsRecording: false, at: t(0))

        XCTAssertFalse(sm.isRecording)
    }

    func test_sync_fixesStuckFalse_afterGrace() {
        var sm = makeSM()
        sm.sync(tcaIsRecording: true, at: t(5.0))

        XCTAssertTrue(sm.isRecording)
    }
}
