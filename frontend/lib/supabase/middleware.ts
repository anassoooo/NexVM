import { createServerClient } from "@supabase/ssr";
import { type NextRequest, NextResponse } from "next/server";

function isSessionExpiryError(error: unknown): boolean {
  if (!error || typeof error !== "object") return false;
  const err = error as { name?: string; status?: number };
  if (err.name === "AuthSessionMissingError") return true;
  if (err.status === 400 || err.status === 403) return true;
  return false;
}

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({
    request: {
      headers: request.headers,
    },
  });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          );
          supabaseResponse = NextResponse.next({
            request,
          });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();

  const isAuthRoute =
    request.nextUrl.pathname.startsWith("/login") ||
    request.nextUrl.pathname.startsWith("/signup");

  if ((!user || error) && !isAuthRoute) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";

    const hadStaleSession =
      request.cookies.getAll().some((c) => c.name.includes("-auth-token")) &&
      isSessionExpiryError(error);

    if (hadStaleSession) {
      url.searchParams.set("reason", "session_expired");
    }

    const redirectResponse = NextResponse.redirect(url);

    const responseCookieNames = new Set(
      supabaseResponse.cookies.getAll().map((c) => c.name)
    );
    supabaseResponse.cookies.getAll().forEach((cookie) => {
      if (cookie.name.includes("-auth-token")) {
        redirectResponse.cookies.set(cookie.name, "", { maxAge: 0 });
      } else {
        redirectResponse.cookies.set(cookie);
      }
    });
    request.cookies.getAll().forEach((cookie) => {
      if (
        cookie.name.includes("-auth-token") &&
        !responseCookieNames.has(cookie.name)
      ) {
        redirectResponse.cookies.set(cookie.name, "", { maxAge: 0 });
      }
    });

    return redirectResponse;
  }

  if (user && isAuthRoute) {
    const url = request.nextUrl.clone();
    url.pathname = "/dashboard";
    const redirectResponse = NextResponse.redirect(url);
    supabaseResponse.cookies.getAll().forEach((cookie) => {
      redirectResponse.cookies.set(cookie);
    });
    return redirectResponse;
  }

  return supabaseResponse;
}
