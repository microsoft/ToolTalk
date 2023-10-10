from .account import (
    AccountSuite,
    ChangePassword,
    DeleteAccount,
    GetAccountInformation,
    LogoutUser,
    QueryUser,
    RegisterUser,
    ResetPassword,
    SendVerificationCode,
    UpdateAccountInformation,
    UserLogin
)
from .alarm import (
    AlarmSuite,
    AddAlarm,
    DeleteAlarm,
    FindAlarms
)
from .calendar import (
    CalendarSuite,
    CreateEvent,
    DeleteEvent,
    ModifyEvent,
    QueryCalendar
)
from .email import (
    EmailSuite,
    SearchInbox,
    SendEmail
)
from .message import (
    MessagesSuite,
    SearchMessages,
    SendMessage
)
from .reminder import (
    ReminderSuite,
    AddReminder,
    CompleteReminder,
    DeleteReminder,
    GetReminders
)
# maybe delete weather out of laziness
from .weather import (
    WeatherSuite,
    CurrentWeather,
    ForecastWeather,
    HistoricWeather
)

ALL_APIS = [
    # Account
    ChangePassword,
    DeleteAccount,
    GetAccountInformation,
    LogoutUser,
    QueryUser,
    RegisterUser,
    ResetPassword,
    SendVerificationCode,
    UpdateAccountInformation,
    UserLogin,
    # Alarm
    AddAlarm,
    DeleteAlarm,
    FindAlarms,
    # Calendar
    CreateEvent,
    DeleteEvent,
    ModifyEvent,
    QueryCalendar,
    # Email
    SearchInbox,
    SendEmail,
    # Message
    SearchMessages,
    SendMessage,
    # Reminder
    AddReminder,
    CompleteReminder,
    DeleteReminder,
    GetReminders,
    # Weather
    CurrentWeather,
    ForecastWeather,
    HistoricWeather
]
ALL_SUITES = [
    AccountSuite,
    AlarmSuite,
    CalendarSuite,
    EmailSuite,
    MessagesSuite,
    ReminderSuite,
    WeatherSuite
]
APIS_BY_NAME = {api.__name__: api for api in ALL_APIS}
SUITES_BY_NAME = {suite.name: suite for suite in ALL_SUITES}
