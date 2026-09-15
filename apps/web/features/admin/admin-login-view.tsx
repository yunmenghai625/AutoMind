"use client";

import { LockKeyhole, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { HttpClientError } from "@/lib/api/apiClient";
import { getCurrentUser, loginAdmin } from "@/lib/api/authApi";
import { getAccessToken, setAccessToken } from "@/lib/api/identity";

export function AdminLoginView() {
  const router = useRouter();
  const [username, setUsername] = React.useState("yunmenghai625");
  const [password, setPassword] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!getAccessToken()) return;
    void getCurrentUser()
      .then((user) => {
        if (user.role === "admin") router.replace("/admin");
      })
      .catch(() => undefined);
  }, [router]);

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!username.trim() || !password || loading) return;
    setLoading(true);
    setError(null);
    try {
      const session = await loginAdmin(username.trim(), password);
      setAccessToken(session.accessToken);
      router.replace("/admin");
    } catch (cause) {
      if (cause instanceof HttpClientError && cause.code === "ADMIN_LOGIN_NOT_CONFIGURED") {
        setError("管理员账号尚未在服务器中启用。");
      } else {
        setError("管理员账号或密码错误。");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto flex min-h-[70vh] max-w-md items-center px-4 py-10">
      <Card className="w-full">
        <CardHeader className="text-center">
          <span className="mx-auto mb-2 flex h-11 w-11 items-center justify-center rounded-full bg-primary/10 text-primary">
            <ShieldCheck className="h-5 w-5" />
          </span>
          <CardTitle>管理员登录</CardTitle>
          <CardDescription>登录后可进入 AutoMind 运营管理看板。</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={submit}>
            <label className="block space-y-1.5 text-sm">
              <span className="font-medium">管理员账号</span>
              <Input
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                autoComplete="username"
                disabled={loading}
              />
            </label>
            <label className="block space-y-1.5 text-sm">
              <span className="font-medium">密码</span>
              <Input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                disabled={loading}
              />
            </label>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button className="w-full" type="submit" disabled={loading}>
              <LockKeyhole className="h-4 w-4" />
              {loading ? "正在验证…" : "登录运营管理"}
            </Button>
          </form>
          <p className="mt-4 text-center text-xs text-muted-foreground">
            管理员会话最长保持 8 小时，请勿在公共设备上登录。
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
