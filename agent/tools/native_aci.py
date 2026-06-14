import subprocess
import psutil
import platform

def check_and_kill_port(port: int) -> str:
    """
    检查指定端口是否被占用，如果被占用则定位 PID 并强制结束进程。
    这是展示 Agent 拥有底层原生操作系统控制权的核心用例。
    """
    if platform.system() != "Windows":
        return f"Port management currently optimized for Windows. Current OS: {platform.system()}"
    
    try:
        # Find PID using netstat
        result = subprocess.run(f"netstat -ano | findstr :{port}", capture_output=True, text=True, shell=True)
        lines = result.stdout.strip().split('\n')
        if not lines or lines[0] == "":
            return f"端口 {port} 目前畅通，未被占用。"
            
        # Extract PID from the first matching line (assuming LISTENING state is usually first)
        pid = None
        for line in lines:
            if "LISTENING" in line:
                pid = line.strip().split()[-1]
                break
        
        if not pid:
            pid = lines[0].strip().split()[-1]
            
        # Get process info
        process = psutil.Process(int(pid))
        pname = process.name()
        
        # Kill the process
        process.kill()
        
        return f"[自愈成功] 发现端口 {port} 被进程 '{pname}' (PID: {pid}) 占用，已向底层发送 SIGKILL 信号并成功终止该进程。"
    except psutil.NoSuchProcess:
        return f"尝试终止端口 {port} 对应的进程时失败，进程可能已经退出。"
    except psutil.AccessDenied:
        return f"[权限不足] 端口 {port} 被占用，但 天韬（SkyT） 缺乏管理员权限(Administrator) 强制终止该进程。"
    except Exception as e:
        return f"[执行错误] 管理端口 {port} 时发生异常: {str(e)}"

def get_system_resources() -> str:
    """
    获取底层硬件的实时占用率 (CPU, 内存)。
    """
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        
        report = (
            f"💻 系统硬件实时报告:\n"
            f"- CPU 占用率: {cpu}%\n"
            f"- 物理内存占用率: {mem.percent}%\n"
            f"- 已用内存: {round(mem.used / (1024**3), 2)} GB / {round(mem.total / (1024**3), 2)} GB\n"
        )
        return report
    except Exception as e:
        return f"[执行错误] 获取系统资源失败: {str(e)}"

def check_weather_local(gps_location: dict = None) -> str:
    """
    通过 GPS 或 IP 定位并获取当地实时天气。包含代理检测，全面中文化与口语化。
    """
    import urllib.request
    import json
    import ssl
    import time
    
    WEATHER_TRANS = {
        "Clear": "晴朗", "Sunny": "晴天", "Partly cloudy": "多云", "Cloudy": "多云转阴",
        "Overcast": "阴天", "Mist": "薄雾", "Patchy rain possible": "可能有零星阵雨",
        "Patchy rain nearby": "附近有零星阵雨", "Patchy snow possible": "可能有零星降雪", 
        "Patchy sleet possible": "可能有零星雨夹雪", "Patchy freezing drizzle possible": "可能有零星冻毛毛雨", 
        "Thundery outbreaks possible": "可能有雷暴", "Blowing snow": "吹雪", "Blizzard": "暴风雪", 
        "Fog": "雾", "Freezing fog": "冻雾", "Patchy light drizzle": "零星细毛毛雨", 
        "Light drizzle": "细毛毛雨", "Freezing drizzle": "冻毛毛雨", "Heavy freezing drizzle": "强冻毛毛雨", 
        "Patchy light rain": "零星小雨", "Light rain": "小雨", "Moderate rain at times": "时有中雨", 
        "Moderate rain": "中雨", "Heavy rain at times": "时有大雨", "Heavy rain": "大雨", 
        "Light freezing rain": "小冻雨", "Moderate or heavy freezing rain": "中到大冻雨",
        "Light sleet": "小雨夹雪", "Moderate or heavy sleet": "中到大雨夹雪", "Patchy light snow": "零星小雪",
        "Light snow": "小雪", "Patchy moderate snow": "零星中雪", "Moderate snow": "中雪",
        "Patchy heavy snow": "零星大雪", "Heavy snow": "大雪", "Ice pellets": "冰粒",
        "Light rain shower": "小阵雨", "Moderate or heavy rain shower": "中到大阵雨",
        "Torrential rain shower": "暴雨", "Light sleet showers": "小雨夹雪阵雨",
        "Moderate or heavy sleet showers": "中到大雨夹雪阵雨", "Light snow showers": "小阵雪",
        "Moderate or heavy snow showers": "中到大阵雪", "Light showers of ice pellets": "小冰粒阵雨",
        "Moderate or heavy showers of ice pellets": "中到大冰粒阵雨", "Patchy light rain with thunder": "零星雷阵雨",
        "Moderate or heavy rain with thunder": "中到大雷阵雨", "Patchy light snow with thunder": "零星雷阵雪",
        "Moderate or heavy snow with thunder": "中到大雷阵雪"
    }

    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        city = "北京"
        region = "中国"
        query_target = ""
        
        if gps_location and 'lat' in gps_location and 'lon' in gps_location:
            query_target = f"{gps_location['lat']},{gps_location['lon']}"
            # 尝试通过反向地理编码获取中文地名
            try:
                rev_url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={gps_location['lat']}&lon={gps_location['lon']}&accept-language=zh-CN"
                req_rev = urllib.request.Request(rev_url, headers={'User-Agent': 'SkyT-Agent/1.0'})
                opener_rev = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                with opener_rev.open(req_rev, timeout=3) as resp_rev:
                    addr = json.loads(resp_rev.read().decode('utf-8')).get('address', {})
                    city = addr.get('city', addr.get('town', addr.get('county', '高精度位置')))
                    region = addr.get('state', addr.get('province', '中国'))
            except Exception:
                city = "高精度GPS定位点"
                region = "您所在的"
        else:
            country_code = "CN"
            try:
                req = urllib.request.Request("http://ip-api.com/json/?lang=zh-CN", headers={'User-Agent': 'Mozilla/5.0'})
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                with opener.open(req, timeout=3) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    if data.get('status') == 'success':
                        city = data.get('city', '北京')
                        region = data.get('regionName', '中国')
                        country_code = data.get('countryCode', 'CN')
                        query_target = city
            except Exception:
                query_target = city
                
            tz = time.tzname[0]
            if country_code != "CN" and ("中国" in tz or "China" in tz or time.timezone == -28800):
                city = "北京"
                region = "中国"
                query_target = "Beijing"

        # 模拟连接中国气象局API (底层依旧使用高可用源)
        try:
            weather_url = f"http://wttr.in/{urllib.parse.quote(query_target)}?format=j1"
            req_w = urllib.request.Request(weather_url, headers={'User-Agent': 'curl/7.68.0'})
            opener_w = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener_w.open(req_w, timeout=5) as resp:
                weather_data = json.loads(resp.read().decode('utf-8'))
                
            current = weather_data['current_condition'][0]
            temp_c = current['temp_C']
            humidity = current['humidity']
            precip = current['precipMM']
            
            raw_desc = current['weatherDesc'][0]['value'].strip()
            desc = WEATHER_TRANS.get(raw_desc, raw_desc)
            
            if not (gps_location and 'lat' in gps_location):
                if 'nearest_area' in weather_data:
                    area = weather_data['nearest_area'][0]
                    api_city = area.get('areaName', [{}])[0].get('value', city)
                    api_region = area.get('region', [{}])[0].get('value', region)
                    if not any(char >= '\u4e00' and char <= '\u9fff' for char in api_city):
                        pass # 如果是拼音/英文，则不覆盖中文IP地名
                    else:
                        city = api_city
                        region = api_region
                        
            return f"您所在的位置是【{region}{city}】，当前天气为{desc}，温度为 {temp_c}°C，相对湿度 {humidity}%，降水量为 {precip} 毫米。"
        except Exception as e:
            return f"您所在的位置是【{region}{city}】，目前天气晴朗，温度约为 25°C，湿度 50%。(注：因气象接口网络波动，此为系统预设模拟数据)"
            
    except Exception as e:
        return f"获取气象失败，请稍后重试。"

def execute_system_command(cmd: str) -> str:
    """
    真正的“上帝之手”：静默在宿主机执行终端命令。
    捕获标准输出和标准错误返回。
    """
    try:
        # Use subprocess to run the command in the native OS shell
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            shell=True,
            encoding='utf-8', 
            errors='replace'
        )
        
        output = result.stdout.strip()
        error = result.stderr.strip()
        
        if result.returncode == 0:
            return f"[执行成功]\n{output}" if output else "[执行成功，无输出]"
        else:
            return f"[执行失败 (退出码 {result.returncode})]\nSTDOUT: {output}\nSTDERR: {error}"
            
    except Exception as e:
        return f"[执行异常] {str(e)}"
