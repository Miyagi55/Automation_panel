#!/usr/bin/env python3
"""
Test script for cross-platform notifications.
"""

import sys
import time
from pathlib import Path

# Add the app directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from app.utils.notifications import notification_manager


def test_basic_notification():
    """Test basic notification functionality."""
    print("Testing basic notification...")
    success = notification_manager.show_notification(
        title="Test Notification",
        message="This is a test message from the Automation Panel",
        notification_type="test",
        duration=5,
        threaded=False,
    )
    print(f"Basic notification result: {'Success' if success else 'Failed'}")
    return success


def test_system_alerts():
    """Test system alert notifications."""
    print("\nTesting system alert notifications...")

    # Test memory alert
    print("- Testing memory alert...")
    success1 = notification_manager.show_memory_alert(85.5, 2.1)

    time.sleep(2)

    # Test CPU alert
    print("- Testing CPU alert...")
    success2 = notification_manager.show_cpu_alert(95.2)

    time.sleep(2)

    # Test storage alert
    print("- Testing storage alert...")
    success3 = notification_manager.show_storage_alert(78.9, 45.2)

    time.sleep(2)

    # Test captcha alert
    print("- Testing captcha alert...")
    success4 = notification_manager.show_captcha_alert("test_account_123")

    results = [success1, success2, success3, success4]
    print(f"System alerts result: {sum(results)}/{len(results)} successful")
    return all(results)


def test_rate_limiting():
    """Test notification rate limiting."""
    print("\nTesting rate limiting...")

    # Show first notification
    success1 = notification_manager.show_notification(
        title="Rate Limit Test",
        message="First notification",
        notification_type="rate_test",
        threaded=False,
    )

    # Try to show second notification immediately (should be rate limited)
    success2 = notification_manager.show_notification(
        title="Rate Limit Test",
        message="Second notification (should be blocked)",
        notification_type="rate_test",
        threaded=False,
    )

    print(
        f"Rate limiting test: First={success1}, Second={success2} (expected: True, False)"
    )
    return success1 and not success2


def test_configuration():
    """Test notification configuration options."""
    print("\nTesting configuration options...")

    # Test app name setting
    notification_manager.set_app_name("Test App")

    # Test cooldown setting
    notification_manager.set_cooldown(60)

    # Test enabling/disabling
    notification_manager.set_enabled(False)
    disabled_result = notification_manager.show_notification(
        title="Disabled Test", message="This should not show", threaded=False
    )

    notification_manager.set_enabled(True)
    enabled_result = notification_manager.show_notification(
        title="Enabled Test", message="This should show", threaded=False
    )

    print(f"Configuration test: Disabled={disabled_result}, Enabled={enabled_result}")
    return not disabled_result and enabled_result


def test_threading():
    """Test threaded notifications."""
    print("\nTesting threaded notifications...")

    # Show multiple threaded notifications
    results = []
    for i in range(3):
        success = notification_manager.show_notification(
            title=f"Threaded Test {i+1}",
            message=f"This is threaded notification #{i+1}",
            notification_type=f"thread_test_{i}",
            duration=3,
            threaded=True,
        )
        results.append(success)
        time.sleep(0.5)  # Small delay between notifications

    print(f"Threading test: {sum(results)}/{len(results)} successful")
    return all(results)


def main():
    """Run all notification tests."""
    print("=" * 50)
    print("Cross-Platform Notification System Test")
    print("=" * 50)

    # Check if notifications are available
    from app.utils.notifications import PLYER_AVAILABLE, SYSTEM_PLATFORM

    print(f"Platform: {SYSTEM_PLATFORM}")
    print(f"Plyer available: {PLYER_AVAILABLE}")

    if not PLYER_AVAILABLE:
        print("❌ Plyer not available - notifications will not work")
        return False

    # Run tests
    tests = [
        ("Basic Notification", test_basic_notification),
        ("System Alerts", test_system_alerts),
        ("Rate Limiting", test_rate_limiting),
        ("Configuration", test_configuration),
        ("Threading", test_threading),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"✅ {test_name}: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            results.append((test_name, False))
            print(f"❌ {test_name}: ERROR - {e}")

        print("-" * 30)
        time.sleep(1)  # Brief pause between tests

    # Summary
    passed = sum(1 for _, result in results if result)
    total = len(results)

    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Notification system is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
