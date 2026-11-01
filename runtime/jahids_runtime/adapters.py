"""NVIDIA NIM and opt-in local process adapters. No shell invocation."""
import json
import os
import shutil
import subprocess
import urllib.request

class AdapterError(RuntimeError):
    pass

class NvidiaNimAdapter:
    def run(self, prompt):
        key = os.getenv("NVIDIA_API_KEY")
        if not key:
            raise AdapterError("NVIDIA_API_KEY is not configured")
        body = json.dumps({"model":os.getenv("JAHIDS_NIM_MODEL","minimaxai/minimax-m3.1"),"messages":[{"role":"user","content":prompt}],"temperature":0.2,"max_tokens":2048}).encode()
        req = urllib.request.Request(os.getenv("NVIDIA_BASE_URL","https://integrate.api.nvidia.com/v1") + "/chat/completions", data=body, headers={"Authorization":"Bearer " + key,"Content-Type":"application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                payload = json.loads(response.read().decode())
            return {"provider":"nvidia-nim","text":payload["choices"][0]["message"]["content"]}
        except Exception as exc:
            raise AdapterError("NVIDIA NIM request failed: " + type(exc).__name__) from exc

class LocalAgentAdapter:
    def __init__(self, name, env_name, expected):
        self.name, self.env_name, self.expected = name, env_name, expected
    def run(self, prompt):
        if os.getenv("JAHIDS_ENABLE_LOCAL_AGENTS","false").lower() != "true":
            raise AdapterError("local agent execution is disabled")
        try:
            argv = json.loads(os.getenv(self.env_name,""))
        except json.JSONDecodeError as exc:
            raise AdapterError(self.env_name + " must be a JSON argv array") from exc
        if not isinstance(argv,list) or not argv or not all(isinstance(x,str) for x in argv):
            raise AdapterError(self.env_name + " must be a non-empty string array")
        executable = shutil.which(argv[0])
        if not executable or os.path.basename(executable) != self.expected:
            raise AdapterError("configured executable must resolve to " + self.expected)
        try:
            result = subprocess.run([executable,*argv[1:],prompt],capture_output=True,text=True,timeout=300,check=False,shell=False,env={"PATH":os.getenv("PATH",""),"HOME":os.getenv("HOME","")})
        except subprocess.TimeoutExpired as exc:
            raise AdapterError("local agent timed out") from exc
        if result.returncode:
            raise AdapterError(self.name + " exited with status " + str(result.returncode))
        return {"provider":self.name,"text":result.stdout[-20000:]}

class AdapterRegistry:
    def __init__(self):
        self.adapters = {"nvidia-nim":NvidiaNimAdapter(),"openclaw":LocalAgentAdapter("openclaw","JAHIDS_OPENCLAW_ARGV","openclaw"),"hermes":LocalAgentAdapter("hermes","JAHIDS_HERMES_ARGV","hermes")}
    def run(self, provider, prompt):
        if provider not in self.adapters:
            raise AdapterError("unknown provider")
        return self.adapters[provider].run(prompt)
