#!/usr/bin/env python3
"""
Key to Data Type Mapper
-----------------------
将 traffic 中的 key 映射到 data_synonyms.yml 定义的 118 个 data types。

映射策略（优先级从高到低）：
1. 精确匹配：key name 完全匹配 known_key_map
2. Fixed-value patterns: key + value 联合匹配
3. 精确匹配 phrase_to_term
4. 包含匹配：key 包含某个 phrase
5. 值正则匹配
"""

import json
import re
import yaml
from pathlib import Path
from typing import Optional, Tuple, Dict, List, Set
from collections import defaultdict, OrderedDict


    # Keys that should NEVER be matched by phrase_contains (HTTP headers, SDK fields, etc.)
BLACKLISTED_KEYS = {
    # --- Standard HTTP headers ---
    'accept', 'accept-charset', 'accept-encoding', 'accept-language', 'accept-ranges',
    'access-control-allow-credentials', 'access-control-allow-headers',
    'access-control-allow-methods', 'access-control-allow-origin',
    'access-control-expose-headers', 'access-control-max-age',
    'access-control-request-headers', 'access-control-request-method',
    'age', 'allow', 'alt-svc', 'authorization', 'cache-control',
    'connection', 'content-disposition', 'content-encoding', 'content-language',
    'content-length', 'content-location', 'content-range', 'content-security-policy',
    'content-type', 'cookie', 'date', 'etag', 'expect', 'expires',
    'forwarded', 'from', 'host', 'if-match', 'if-modified-since',
    'if-none-match', 'if-range', 'if-unmodified-since', 'keep-alive',
    'last-modified', 'link', 'location', 'max-forwards', 'origin',
    'pragma', 'proxy-authenticate', 'proxy-authorization', 'proxy-connection',
    'range', 'referer', 'referrer', 'retry-after', 'server',
    'set-cookie', 'strict-transport-security', 'te', 'trailer',
    'transfer-encoding', 'upgrade', 'user-agent', 'vary', 'via',
    'warning', 'www-authenticate', 'x-forwarded-for', 'x-forwarded-host',
    'x-forwarded-proto', 'x-real-ip', 'x-request-id', 'x-requested-with',
    # --- Common X- headers ---
    'x-headers-hash', 'x-amz-signedheaders', 'x-amz-signature', 'x-amz-credential',
    'x-amz-date', 'x-amz-security-token', 'x-amz-algorithm', 'x-amz-content-sha256',
    'x-client-bundle-id', 'x-client-data', 'x-client-info', 'x-client-library',
    'x-mme-client-info', 'x-unity-version', 'x-platform-version', 'x-platform-flavor',
    'x-youtube-client-version', 'x-youtube-client-name', 'x-youtube-device',
    'x-youtube-page-label', 'x-youtube-time-zone',
    'x-bamsdk-platform', 'x-bamsdk-version', 'x-bamsdk-client-id',
    'x-wbd-session-state', 'x-wbd-time-zone',
    'x-datadog-tags', 'x-datadog-origin', 'x-datadog-trace-id', 'x-datadog-parent-id',
    'x-datadog-sampling-priority',
    'x-observer-mode-enabled', 'x-is-debug-build', 'x-apple-signature',
    'x-apple-content-partition', 'x-ios-bundle-identifier',
    'x-apple-persistent-identifier', 'x-apollo-operation-type',
    'x-firebase-rc-fetch-type', 'x-office-platform',
    'x-post-params-hash', 'x-goog-visitor-id', 'x-slack-signature',
    'x-braze-contentcardsrequest', 'x-timezone', 'x-timezone-offset',
    'x-request-yp-id', 'x-caller-id', 'x-postal-code',
    # --- Distributed tracing ---
    'sentry-trace', 'traceparent', 'tracestate', 'x-b3-traceid', 'x-b3-spanid',
    'x-b3-parentspanid', 'x-b3-sampled', 'x-trace-id', 'x-span-id',
    'x-request-trace-id', 'baggage',
    # --- CORS / preflight ---
    'sec-fetch-dest', 'sec-fetch-mode', 'sec-fetch-site', 'sec-ch-ua',
    'sec-ch-ua-mobile', 'sec-ch-ua-platform',
    # --- Common SDK/technical keys ---
    'namespace', 'operationname', 'content-byte-range', 'upload-complete',
    'service-worker', 'callback', 'jscallback',
    'reducedmotion', 'cplayer', 'cplatform', 'adapty-sdk-observer-mode-enabled',
    'adapty-sdk-previous-response-hash', 'adapty-profile-segment-hash',
    # --- OpenTelemetry / metrics (prefix patterns handled separately) ---
}

# Key PREFIXES that should be blacklisted for phrase_contains
BLACKLISTED_KEY_PREFIXES = [
    'resourcemetrics[', 'resourcemetrics.', 'scopemetrics[', 'scopemetrics.',
    'access-control-', 'sec-fetch-', 'sec-ch-',
    'headless.', '_isheadless', 'weblabtreatmentmap.',
    'sharedproperties.', 'navigationproperties.',
]

# Phrases that are too short/generic for substring matching and cause massive false positives
BLACKLISTED_PHRASES = {
    'head', 'heading',        # face: matches HTTP headers
    'race',                   # ethnic: matches trace/traceparent
    'client',                 # person name: matches x-client-*
    'name',                   # person name: matches namespace, operationName
    'text',                   # message log: matches content-type text
    'data',                   # information: matches datadog, metadata
    'content',                # usage info: matches content-encoding
    'request',                # information: matches access-control-request
    'user',                   # account: matches user-agent
    'stat',                   # gameplay: matches session-state
    'visitor',                # gameplay: matches x-goog-visitor-id
    'token',                  # password: matches cart_token, OAuth tokens
    'credential',             # password: matches X-Amz-Credential
    'attribute',              # body measure: matches OpenTelemetry attributes
    'platform',               # usage info: matches x-platform-*
    'server',                 # usage info: matches x-observer-mode-enabled
    'metadata',               # information: matches mp_metadata
    'detail',                 # information: matches sdetail
    'resource',               # education: matches resourceMetrics
    'grade',                  # education: matches Upgrade header
    'feature',                # pii: matches feature flags
    'upload',                 # pii: matches upload-complete
    'call',                   # phone num: matches callback
    'area',                   # geo location: matches ShareAvailable
    'code',                   # gameplay: matches code_challenge (OAuth)
    'play',                   # gameplay: matches displayMode, playlistId
    'library',                # gameplay: matches x-client-library
    'page',                   # browsing: matches x-youtube-page-label
    'setting',                # gameplay: matches settingRemindersEnabled
    'level',                  # usage info: matches topLevelDomain
    'access',                 # usage info: matches radioaccesstechnology
    'product',                # usage info: matches pro_product_id
    'share',                  # information: matches sharedProperties
    'view',                   # usage info: matches viewMode
    'cookie',                 # information: matches cookie fields
    'refer',                  # browsing: matches referer HTTP header
    'connect',                # network: matches Proxy-Connection
    'send',                   # usage info: matches tsEndpoint
    'service',                # usage info: matches service-worker
    'vehicle',                # geo location: vehicle != location
    'person',                 # sexuality: matches person_properties
    'embed',                  # audio: matches embedUrl
    'motion',                 # vr movement: matches reducedMotion (accessibility)
    'place',                  # geo location: matches placement, marketplace
    'player',                 # account: matches cplayer (media player)
    'body',                   # body measure: matches body_style (vehicle)
    'mobile',                 # type: matches mobile_app
    'handle',                 # user id: matches assoc_handle
    'badge',                  # gameplay: matches app badge
    'input',                  # pii: matches variables.input
    'query',                  # pii: matches persistedQuery
    'support',                # pii: matches touchSupport
    'card',                   # billing: matches contentcardsrequest
    'external',               # information: matches externalBaseUrl
    'traffic',                # information: matches traffictype
    'exchange',               # billing: matches exchangeDeviceGrant
    'marketing',              # billing: matches marketingContentCreativeId
    'application',            # usage info: matches application.schemaUri
    'system',                 # gameplay: matches systemProps
    'room',                   # gameplay: matches livingRoomAppMode
    'click',                  # browsing: matches ClickId (ad tracking)
    'site',                   # browsing: matches appDefinitionIdToSiteRevision
    'browse',                 # browsing: matches browseId
    'conversation',           # message log: matches conversationId
    'notification',           # message log: matches enabledNotifications
    'image',                  # photo: matches style_transfer_num_images
}


class KeyToDataTypeMapper:
    def __init__(self, synonyms_path: str = None, extra_rules_path: str = None):
        self.phrase_to_term: Dict[str, str] = {}
        self.term_phrases: Dict[str, List[str]] = {}
        self.regex_rules: List[Tuple[str, str, re.Pattern]] = []
        self.known_key_map: Dict[str, str] = {}
        self.compiled_fixed_patterns = OrderedDict()
        
        # 先加载 config.yaml（优先级高）
        if extra_rules_path:
            self._load_extra_rules(extra_rules_path)
        
        # 然后加载 synonyms（优先级低，不会覆盖 config.yaml 的规则）
        if synonyms_path:
            self._load_synonyms(synonyms_path)
        
        # 最后加载内置规则（作为 fallback，不会覆盖已有的规则）
        self._init_builtin_rules()
    
    def _load_synonyms(self, path: str):
        with open(path, 'r', encoding='utf-8') as f:
            synonyms = yaml.safe_load(f)
        
        self.term_phrases = synonyms
        
        # 从 synonyms 构建 known_key_map（phrase -> data_type）
        # 这些是来自 synonym 文件的 key mappings
        synonym_key_map = {}
        for data_type, phrases in synonyms.items():
            for phrase in phrases:
                phrase_clean = phrase.strip().lower()
                if phrase_clean:
                    self.phrase_to_term[phrase_clean] = data_type
                    # 如果 phrase 看起来像一个 key name（不包含空格），也加入 known_key_map
                    if ' ' not in phrase_clean and len(phrase_clean) > 1:
                        synonym_key_map[phrase_clean] = data_type
        
        # 合并到 known_key_map（synonym 的优先级较低，config.yaml 的优先级较高）
        # 只添加不在 known_key_map 中的 key（避免覆盖 config.yaml 的规则）
        added_count = 0
        for k, v in synonym_key_map.items():
            if k not in self.known_key_map:
                self.known_key_map[k] = v
                added_count += 1
        
        print(f"[Mapper] Loaded {len(self.phrase_to_term)} phrases -> {len(synonyms)} data types")
        if added_count > 0:
            print(f"[Mapper] Extracted {added_count} key mappings from synonyms (merged with config.yaml)")
    
    def _load_extra_rules(self, path: str):
        """从 config.yaml 加载规则"""
        with open(path, 'r', encoding='utf-8') as f:
            if path.endswith('.yaml') or path.endswith('.yml'):
                config = yaml.safe_load(f)
            else:
                config = json.load(f)
        
        # 加载 known_key_map（从 rules.known_key_map）
        rules = config.get('rules', {})
        if 'known_key_map' in rules:
            # 合并到 known_key_map（config.yaml 的优先级高于 synonym）
            for k, v in rules['known_key_map'].items():
                k_lower = k.lower()
                self.known_key_map[k_lower] = v
            print(f"[Mapper] Loaded {len(rules['known_key_map'])} known_key_map entries from config.yaml")
        
        # 加载 regex 规则（从 rules.regex）
        if 'regex' in rules:
            for rule in rules['regex']:
                name = rule.get('name', 'unnamed')
                target = rule.get('target')
                pattern = rule.get('pattern')
                if target and pattern:
                    try:
                        compiled = re.compile(pattern, re.IGNORECASE)
                        self.regex_rules.append((name, target, compiled))
                    except re.error as e:
                        print(f"[Mapper] Invalid regex pattern '{pattern}': {e}")
            print(f"[Mapper] Loaded {len(rules['regex'])} regex rules from config.yaml")
        
        # 加载 fixed_value_patterns
        if 'fixed_value_patterns' in config:
            fixed_patterns = config['fixed_value_patterns']
            for data_type, patterns_config in fixed_patterns.items():
                label = patterns_config.get('label', data_type)
                key_patterns = patterns_config.get('key_patterns', [])
                value_patterns = patterns_config.get('value_patterns', [])
                
                # 编译 patterns
                compiled_key_patterns = [re.compile(p, re.IGNORECASE) for p in key_patterns]
                compiled_value_patterns = [re.compile(p, re.IGNORECASE) for p in value_patterns]
                
                # 添加到 compiled_fixed_patterns（如果不存在）
                if label not in self.compiled_fixed_patterns:
                    self.compiled_fixed_patterns[label] = {
                        'key_patterns': compiled_key_patterns,
                        'value_patterns': compiled_value_patterns
                    }
                else:
                    # 合并（避免重复）
                    existing = self.compiled_fixed_patterns[label]
                    for kp in compiled_key_patterns:
                        if kp not in existing['key_patterns']:
                            existing['key_patterns'].append(kp)
                    for vp in compiled_value_patterns:
                        if vp not in existing['value_patterns']:
                            existing['value_patterns'].append(vp)
            print(f"[Mapper] Loaded {len(fixed_patterns)} fixed_value_patterns from config.yaml")
    
    def _init_builtin_rules(self):
        """初始化内置规则 - 包含 config.yaml 中的所有规则"""
        
        # ========== Fixed-value patterns (key + value 联合匹配) ==========
        # 顺序很重要：更精确的 pattern 放前面
        fixed_patterns = OrderedDict([
            # 高精度 value patterns（优先匹配）
            ('ip addr', {
                'key_patterns': [r'^ip$', r'ip.*address', r'ipaddress', r'client.*ip', r'user.*ip', r'remote.*addr', r'x-forwarded-for', r'x-real-ip'],
                'value_patterns': [r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$', r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$']
            }),
            ('email addr', {
                'key_patterns': [r'email', r'e-mail', r'e_mail', r'user.*email', r'mail.*address'],
                'value_patterns': [r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$']
            }),
            ('mac addr', {
                'key_patterns': [r'mac.*address', r'macaddress', r'^mac$', r'bssid', r'hardware.*address'],
                'value_patterns': [r'^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$']
            }),
            ('phone num', {
                'key_patterns': [r'phone', r'mobile', r'telephone', r'tel$', r'cell.*number'],
                'value_patterns': [r'^\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$', r'^\+\d{1,3}[-.\s]?\d{4,14}$']
            }),
            ('geo location', {
                'key_patterns': [r'latitude', r'longitude', r'^lat$', r'^lon$', r'^lng$', r'geo.*location', r'geolocation', r'geoip', r'coordinates', r'location.*lat', r'location.*lon'],
                'value_patterns': [r'^-?\d{1,3}\.\d{4,}$', r'^-?\d{1,2}\.\d{4,},-?\d{1,3}\.\d{4,}$']
            }),
            # Device identifiers
            ('device id', {
                'key_patterns': [r'device.*identifier', r'device.*id', r'deviceid', r'udid', r'unique.*device', r'vendor.*id', r'vendorid', r'idfv'],
                'value_patterns': [r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$', r'^[0-9a-fA-F]{32}$']
            }),
            ('ad id', {
                'key_patterns': [r'idfa', r'advertising.*id', r'advertisingid', r'ad.*id', r'adid', r'gaid', r'google.*advertising', r'att.*status'],
                'value_patterns': [r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$', r'^00000000-0000-0000-0000-000000000000$']
            }),
            # Device info
            ('device info', {
                'key_patterns': [r'platform', r'os.*name', r'osname', r'system.*name', r'^\$os$'],
                'value_patterns': [r'^ios$', r'^iphone$', r'^ipad$', r'^visionos$', r'^macos$', r'^android$', r'^windows$', r'^linux$', r'^darwin$', r'^xros$']
            }),
            ('system ver', {
                'key_patterns': [r'os.*version', r'osversion', r'system.*version', r'ios.*version', r'version.*os', r'^\$os_version$', r'systemversion'],
                'value_patterns': [r'^[12]?\d\.\d+(\.\d+)?$']
            }),
            ('app ver', {
                'key_patterns': [r'app.*version', r'appversion', r'app.*build', r'appbuild', r'build.*number', r'cfbundleversion', r'cfbundleshortversionstring'],
                'value_patterns': [r'^v?\d+\.\d+(\.\d+)?$', r'^\d+$']
            }),
            ('model', {
                'key_patterns': [r'device.*model', r'devicemodel', r'hardware.*model', r'hardwaremodel', r'machine', r'hw\.machine'],
                'value_patterns': [r'RealityDevice\d+', r'iPhone\d+,\d+', r'iPad\d+,\d+', r'Mac\d+,\d+', r'AppleTV\d+,\d+']
            }),
            ('language', {
                'key_patterns': [r'language', r'locale', r'^lang$', r'device.*language', r'user.*language'],
                'value_patterns': [r'^[a-z]{2}$', r'^[a-z]{2}[-_][A-Z]{2}$', r'^[a-z]{2}[-_][A-Z][a-z]{3}$']
            }),
            ('browser type', {
                'key_patterns': [r'user.*agent', r'useragent', r'^ua$', r'browser'],
                'value_patterns': [r'Mozilla/5\.0', r'CFNetwork/', r'Darwin/']
            }),
            ('network', {
                'key_patterns': [r'carrier', r'network.*type', r'networktype', r'connection.*type', r'wifi', r'cellular', r'radio'],
                'value_patterns': [r'^wifi$', r'^cellular$', r'^4g$', r'^5g$', r'^lte$', r'^3g$']
            }),
            ('screen', {
                'key_patterns': [r'screen.*width', r'screen.*height', r'screen.*size', r'resolution', r'display.*width', r'display.*height'],
                'value_patterns': [r'^\d{3,4}$', r'^\d{3,4}x\d{3,4}$']
            }),
            # VR specific
            ('vr headset', {
                'key_patterns': [r'headset', r'hmd', r'vr.*device', r'xr.*device', r'vision.*pro'],
                'value_patterns': [r'Apple Vision Pro', r'Quest', r'RealityDevice']
            }),
            ('eye tracking', {
                'key_patterns': [r'eye.*tracking', r'eyetracking', r'gaze', r'pupil', r'eye.*position', r'eye.*direction'],
                'value_patterns': []
            }),
            ('hand tracking', {
                'key_patterns': [r'hand.*tracking', r'handtracking', r'hand.*gesture', r'gesture', r'hand.*position', r'hand.*joint'],
                'value_patterns': []
            }),
            ('vr movement', {
                'key_patterns': [r'head.*pose', r'headpose', r'head.*position', r'head.*rotation', r'head.*tracking', r'6dof', r'3dof'],
                'value_patterns': []
            }),
            ('accelerometer', {
                'key_patterns': [r'accelerometer', r'accel', r'acceleration'],
                'value_patterns': []
            }),
            ('gyroscope', {
                'key_patterns': [r'gyroscope', r'gyro', r'rotation.*rate'],
                'value_patterns': []
            }),
            # Session & User
            ('session', {
                'key_patterns': [r'session.*id', r'sessionid', r'^session$'],
                'value_patterns': [r'^[0-9a-fA-F]{32}$', r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$']
            }),
            ('user id', {
                'key_patterns': [r'user.*id', r'userid', r'^uid$', r'account.*id', r'accountid', r'member.*id', r'player.*id'],
                'value_patterns': []
            }),
            ('usage info', {
                'key_patterns': [r'event', r'action', r'activity', r'behavior', r'usage', r'analytics', r'tracking', r'telemetry'],
                'value_patterns': []
            }),
            ('error report', {
                'key_patterns': [r'crash', r'error', r'exception', r'stacktrace', r'stack.*trace', r'bug.*report', r'diagnostic'],
                'value_patterns': []
            }),
        ])
        
        # 编译 patterns
        for data_type, patterns in fixed_patterns.items():
            self.compiled_fixed_patterns[data_type] = {
                'key_patterns': [re.compile(p, re.IGNORECASE) for p in patterns.get('key_patterns', [])],
                'value_patterns': [re.compile(p, re.IGNORECASE) for p in patterns.get('value_patterns', [])]
            }
        
        # ========== Known key map (精确匹配) ==========
        builtin_key_map = {
            # Email
            'email': 'email addr', 'user_email': 'email addr', 'email_address': 'email addr', 'emailaddress': 'email addr', 'e_mail': 'email addr', 'e-mail': 'email addr',
            # Phone
            'phone': 'phone num', 'phone_number': 'phone num', 'phonenumber': 'phone num', 'mobile': 'phone num', 'mobile_number': 'phone num', 'telephone': 'phone num',
            # Device ID
            'device_id': 'device id', 'deviceid': 'device id', 'udid': 'device id', 'device_identifier': 'device id', 'deviceidentifier': 'device id',
            # Advertising ID
            'idfa': 'ad id', 'idfv': 'device id', 'gaid': 'ad id', 'advertising_id': 'ad id', 'advertisingid': 'ad id', 'adid': 'ad id', 'ad_id': 'ad id',
            # Android ID
            'android_id': 'android id', 'androidid': 'android id',
            # Location
            'lat': 'geo location', 'lon': 'geo location', 'lng': 'geo location', 'latitude': 'geo location', 'longitude': 'geo location',
            'geo': 'geo location', 'geolocation': 'geo location', 'geoip': 'geo location', 'location': 'geo location', 'coordinates': 'geo location',
            # IP
            'ip': 'ip addr', 'ip_address': 'ip addr', 'ipaddress': 'ip addr', 'client_ip': 'ip addr', 'clientip': 'ip addr', 'user_ip': 'ip addr',
            # User ID
            'user_id': 'user id', 'userid': 'user id', 'uid': 'user id', 'account_id': 'account', 'accountid': 'account',
            'username': 'user id', 'user_name': 'user id', 'login': 'user id',
            # Name
            'name': 'person name', 'first_name': 'person name', 'firstname': 'person name', 'last_name': 'person name', 'lastname': 'person name',
            'full_name': 'person name', 'fullname': 'person name', 'display_name': 'person name', 'displayname': 'person name',
            # Age
            'age': 'age', 'birthday': 'age', 'birthdate': 'age', 'birth_date': 'age', 'date_of_birth': 'age', 'dob': 'age',
            # Password
            'password': 'password', 'passwd': 'password', 'pwd': 'password',
            # Device Info
            'device_model': 'device info', 'devicemodel': 'device info', 'model': 'model', 'hardware_model': 'device info',
            'device_name': 'device info', 'devicename': 'device info',
            # OS/System
            'os_version': 'system ver', 'osversion': 'system ver', 'system_version': 'system ver', 'systemversion': 'system ver',
            'platform': 'device info', 'os_name': 'device info', 'osname': 'device info', 'os': 'device info',
            # App Info
            'app_version': 'app ver', 'appversion': 'app ver', 'version': 'app ver', 'build': 'build', 'build_number': 'build',
            # Browser
            'user_agent': 'browser type', 'useragent': 'browser type', 'ua': 'browser type', 'browser': 'browser type',
            # Network
            'carrier': 'network', 'network_type': 'network', 'networktype': 'network', 'wifi': 'network', 'ssid': 'network',
            # Language
            'language': 'language', 'locale': 'language', 'lang': 'language',
            # Session
            'session_id': 'session', 'sessionid': 'session', 'session': 'session',
            # VR specific
            'eye_tracking': 'eye tracking', 'eyetracking': 'eye tracking', 'gaze': 'gaze data',
            'hand_tracking': 'hand tracking', 'handtracking': 'hand tracking',
            'head_pose': 'vr movement', 'headpose': 'vr movement', 'head_position': 'vr movement', 'headposition': 'vr movement',
            'head_rotation': 'vr movement', 'headrotation': 'vr movement',
            'fov': 'vr fov', 'field_of_view': 'vr fov', 'ipd': 'pupil distance', 'pupil_distance': 'pupil distance',
            # Health
            'heart_rate': 'heart rate', 'heartrate': 'heart rate', 'calories': 'calorie', 'steps': 'workout',
            'weight': 'weight', 'height': 'height', 'bmi': 'bmi',
            # Photo/Camera
            'photo': 'photo', 'image': 'photo', 'camera': 'camera', 'picture': 'photo',
            # Audio
            'audio': 'audio', 'voice': 'audio', 'microphone': 'audio', 'mic': 'audio',
            # Contact
            'contact': 'contact', 'contacts': 'contact list', 'address_book': 'contact list', 'addressbook': 'contact list',
            # MAC Address
            'mac': 'mac addr', 'mac_address': 'mac addr', 'macaddress': 'mac addr',
            # Serial Number
            'serial': 'serial num', 'serial_number': 'serial num', 'serialnumber': 'serial num',
            # Usage
            'usage': 'usage info', 'screen_time': 'usage time', 'screentime': 'usage time', 'app_usage': 'usage info', 'appusage': 'usage info',
            # Error/Crash
            'crash': 'error report', 'error': 'error report', 'exception': 'error report', 'stacktrace': 'error report', 'stack_trace': 'error report',
        }
        
        for k, v in builtin_key_map.items():
            if k not in self.known_key_map:
                self.known_key_map[k] = v
        
        # ========== Regex rules (值匹配) ==========
        builtin_regex = [
            ('email_value', 'email addr', r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
            ('ipv4_value', 'ip addr', r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'),
            ('phone_value', 'phone num', r'^\+?\d[\d\s().-]{6,}\d$'),
            ('uuid_device', 'device id', r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
            ('latlon_value', 'geo location', r'^-?\d{1,3}\.\d{4,}$'),
            ('mac_value', 'mac addr', r'^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$'),
        ]
        
        for name, target, pattern in builtin_regex:
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
                self.regex_rules.append((name, target, compiled))
            except re.error:
                pass
    
    def normalize_key(self, key: str) -> str:
        if not key:
            return ""
        key = str(key).strip().lower()
        key = re.sub(r'\[\d+\]', '[]', key)
        return key
    
    def extract_final_keyname(self, key: str) -> str:
        if not key:
            return ""
        key = str(key).strip()
        if key.lower().startswith('cookie.'):
            key = key[7:]
        parts = key.split('.')
        final = parts[-1]
        final = final.split('[')[0]
        return final.strip().lower()
    
    def map_key(self, key: str, value: str = None) -> Optional[Tuple[str, str]]:
        nk = self.normalize_key(key)
        final_key = self.extract_final_keyname(key)
        value_str = str(value).strip() if value else ""
        
        # 1. 精确匹配 known_key_map
        for k in [nk, final_key]:
            k_clean = k.replace('_', '').replace('-', '').replace('$', '')
            if k in self.known_key_map:
                return self.known_key_map[k], f"known_key:{k}"
            if k_clean in self.known_key_map:
                return self.known_key_map[k_clean], f"known_key:{k_clean}"
        
        # 2. Fixed-value patterns
        for data_type, patterns in self.compiled_fixed_patterns.items():
            key_matched = False
            for kp in patterns['key_patterns']:
                if kp.search(nk) or kp.search(final_key) or kp.search(key):
                    key_matched = True
                    if patterns['value_patterns'] and value_str:
                        for vp in patterns['value_patterns']:
                            if vp.search(value_str):
                                return data_type, f"fixed:key+value:{data_type}"
                    elif not patterns['value_patterns']:
                        return data_type, f"fixed:key:{data_type}"
                    break
            
            if not key_matched and patterns['value_patterns'] and value_str:
                for vp in patterns['value_patterns']:
                    if vp.match(value_str):
                        return data_type, f"fixed:value:{data_type}"
        
        # 3. phrase_to_term 精确匹配
        for k in [nk, final_key]:
            k_clean = k.replace('_', ' ').replace('-', ' ')
            if k in self.phrase_to_term:
                return self.phrase_to_term[k], f"phrase:{k}"
            if k_clean in self.phrase_to_term:
                return self.phrase_to_term[k_clean], f"phrase:{k_clean}"
        
        # 4. 包含匹配（改进版：黑名单 + word boundary）
        # 4a. Check if the key itself is blacklisted
        nk_stripped = nk.lstrip('[].$')
        is_blacklisted = (nk_stripped in BLACKLISTED_KEYS or
                          final_key in BLACKLISTED_KEYS)
        if not is_blacklisted:
            for prefix in BLACKLISTED_KEY_PREFIXES:
                if nk_stripped.startswith(prefix):
                    is_blacklisted = True
                    break

        if not is_blacklisted:
            # Tokenize key for word-boundary matching
            # Split by common delimiters: . - _ [] and camelCase boundaries
            def tokenize(s):
                # Replace delimiters with space
                s = re.sub(r'[\.\-_\[\]/:\$]+', ' ', s)
                # Split camelCase: "acceptHeader" -> "accept Header"
                s = re.sub(r'([a-z])([A-Z])', r'\1 \2', s)
                return set(s.lower().split())

            nk_tokens = tokenize(nk)
            fk_tokens = tokenize(final_key)
            all_tokens = nk_tokens | fk_tokens

            for phrase, data_type in self.phrase_to_term.items():
                if len(phrase) < 4:
                    continue
                # Skip blacklisted phrases
                if phrase in BLACKLISTED_PHRASES:
                    continue
                # For single-word phrases: require exact token match
                if ' ' not in phrase:
                    if phrase in all_tokens:
                        return data_type, f"phrase_contains:{phrase}"
                else:
                    # Multi-word phrases: still use substring (they're specific enough)
                    if phrase in nk or phrase in final_key:
                        return data_type, f"phrase_contains:{phrase}"
        
        # 5. 值正则匹配
        if value_str:
            for rule_name, data_type, pattern in self.regex_rules:
                if pattern.match(value_str):
                    return data_type, f"value_regex:{rule_name}"
        
        return None
    
    def get_data_types(self) -> List[str]:
        return list(self.term_phrases.keys())


def create_default_mapper() -> KeyToDataTypeMapper:
    synonyms_path = '/mnt/ssd2/PPAudit/phrase_to_term/synonyms_and_ontologies/data_synonyms.yml'
    config_path = '/mnt/ssd2/VR_monkey/mitmproxy/pipeline/config.yaml'
    return KeyToDataTypeMapper(synonyms_path=synonyms_path, extra_rules_path=config_path)


if __name__ == "__main__":
    mapper = create_default_mapper()
    
    test_cases = [
        ('email', 'test@example.com'),
        ('device_id', '12345678-1234-1234-1234-123456789abc'),
        ('lat', '37.7749295'),
        ('user_agent', 'Mozilla/5.0'),
        ('$os_version', '17.0'),
        ('idfa', '00000000-0000-0000-0000-000000000000'),
        ('cookie.GeoIP', 'US'),
        ('heart_rate', '72'),
        ('random_field', '192.168.1.100'),  # IP value
        ('random_field', 'user@example.com'),  # Email value
        ('hw.machine', 'RealityDevice14'),
        ('unknown_key', 'some_value'),
    ]
    
    print("\nTest mappings:")
    print("-" * 90)
    for key, value in test_cases:
        result = mapper.map_key(key, value)
        if result:
            print(f"{key:<25} {value:<30} -> {result[0]:<15} ({result[1][:25]})")
        else:
            print(f"{key:<25} {value:<30} -> NOT MAPPED")
