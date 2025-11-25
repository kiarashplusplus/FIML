"""
Base Watchdog Class

Provides the abstract base class for all watchdog implementations
with common functionality for monitoring, event emission, and lifecycle management.
"""

import asyncio
import contextlib
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from fiml.core.logging import get_logger
from fiml.watchdog.models import WatchdogEvent, WatchdogHealth

if TYPE_CHECKING:
    from fiml.watchdog.events import EventStream

logger = get_logger(__name__)


class BaseWatchdog(ABC):
    """
    Abstract base class for all watchdogs

    Provides:
    - Async monitoring loop with configurable check intervals
    - Event emission via event stream
    - Health monitoring and status tracking
    - Graceful shutdown handling
    - Error recovery and retry logic

    Subclasses must implement:
    - check(): Perform the actual monitoring check
    - name property: Unique watchdog identifier
    """

    def __init__(
        self,
        check_interval: int = 60,
        enabled: bool = True,
        max_retries: int = 3,
        retry_delay: int = 5,
    ):
        """
        Initialize base watchdog

        Args:
            check_interval: Seconds between checks
            enabled: Whether watchdog is enabled
            max_retries: Maximum retry attempts on error
            retry_delay: Seconds to wait between retries
        """
        self.check_interval = check_interval
        self.enabled = enabled
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Runtime state
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        # Health tracking
        self._health = WatchdogHealth(
            name=self.name,
            status="initialized"
        )
        self._start_time: Optional[datetime] = None
        self._consecutive_errors = 0

        # Event stream (set by orchestrator)
        self._event_stream: Optional["EventStream"] = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique watchdog name"""
        pass

    @abstractmethod
    async def check(self) -> Optional[WatchdogEvent]:
        """
        Perform monitoring check

        Returns:
            WatchdogEvent if anomaly detected, None otherwise

        Raises:
            Exception on check failure
        """
        pass

    def set_event_stream(self, event_stream: "EventStream") -> None:
        """Set the event stream for emitting events"""
        self._event_stream = event_stream

    async def start(self) -> None:
        """Start the watchdog monitoring loop"""
        if not self.enabled:
            logger.info(f"Watchdog {self.name} is disabled, not starting")
            return

        if self._running:
            logger.warning(f"Watchdog {self.name} is already running")
            return

        logger.info(f"Starting watchdog: {self.name}")
        self._running = True
        self._start_time = datetime.now(timezone.utc)
        self._shutdown_event.clear()
        self._health.status = "healthy"

        # Start monitoring loop
        self._task = asyncio.create_task(self._monitoring_loop())

    async def stop(self) -> None:
        """Stop the watchdog monitoring loop gracefully"""
        if not self._running:
            return

        logger.info(f"Stopping watchdog: {self.name}")
        self._running = False
        self._shutdown_event.set()

        # Cancel and wait for task
        if self._task and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

        self._health.status = "stopped"
        logger.info(f"Watchdog {self.name} stopped")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        logger.info(f"Monitoring loop started for {self.name}")

        while self._running and not self._shutdown_event.is_set():
            try:
                # Perform check
                event = await self._check_with_retry()

                # Update health
                self._health.last_check = datetime.now(timezone.utc)
                self._health.total_checks += 1
                self._consecutive_errors = 0
                self._health.consecutive_failures = 0

                # Emit event if anomaly detected
                if event:
                    await self._emit_event(event)

                # Update health status
                self._update_health_status()

            except Exception as e:
                logger.error(f"Error in {self.name} monitoring loop: {e}", exc_info=True)
                self._consecutive_errors += 1
                self._health.errors += 1
                self._health.total_checks += 1
                self._health.consecutive_failures += 1
                self._update_health_status()

            # Wait for next check (with early exit on shutdown)
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self.check_interval
                )
                # If we get here, shutdown was signaled
                break
            except asyncio.TimeoutError:
                # Normal timeout, continue loop
                pass

    async def _check_with_retry(self) -> Optional[WatchdogEvent]:
        """Execute check with retry logic"""
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                return await self.check()
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Check failed for {self.name} (attempt {attempt + 1}/{self.max_retries}): {e}"
                )

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)

        # All retries failed - last_error should not be None here
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"Check failed for {self.name} with no error recorded")

    async def _emit_event(self, event: WatchdogEvent) -> None:
        """Emit event to event stream"""
        if not self._event_stream:
            logger.warning(f"No event stream configured for {self.name}")
            return

        try:
            # Set watchdog name
            event.watchdog = self.name

            # Emit to stream
            await self._event_stream.emit(event)

            # Update health
            self._health.events_emitted += 1
            self._health.last_event = datetime.now(timezone.utc)

            logger.info(
                f"Event emitted by {self.name}: {event.type.value} "
                f"(severity: {event.severity.value})"
            )
        except Exception as e:
            logger.error(f"Failed to emit event from {self.name}: {e}", exc_info=True)
            self._health.errors += 1

    def _update_health_status(self) -> None:
        """Update health status based on errors"""
        if self._consecutive_errors >= self.max_retries:
            self._health.status = "unhealthy"
        elif self._consecutive_errors > 0:
            self._health.status = "degraded"
        else:
            self._health.status = "healthy"

        # Update uptime
        if self._start_time:
            self._health.uptime_seconds = (
                datetime.now(timezone.utc) - self._start_time
            ).total_seconds()

    def get_health(self) -> WatchdogHealth:
        """Get current health status"""
        self._update_health_status()
        return self._health

    def is_running(self) -> bool:
        """Check if watchdog is running"""
        return self._running

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name} status={self._health.status}>"
