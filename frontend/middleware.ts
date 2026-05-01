import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  const token = request.cookies.get("nexvm_token")?.value;
  const isAuthenticated = !!token && token.length > 0;
  const isAdmin = request.cookies.get("nexvm_admin")?.value === "1";
  const { pathname } = request.nextUrl;

  const isAuthRoute = pathname === "/login" || pathname === "/signup";
  const isPublicRoute = pathname === "/";
  const isAdminRoute = pathname.startsWith("/admin");

  if (!isAuthenticated && !isAuthRoute && !isPublicRoute) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.search = "";
    return NextResponse.redirect(url);
  }

  if (isAuthenticated && isAuthRoute) {
    const url = request.nextUrl.clone();
    url.pathname = "/vms";
    url.search = "";
    return NextResponse.redirect(url);
  }

  if (isAuthenticated && isPublicRoute) {
    const url = request.nextUrl.clone();
    url.pathname = isAdmin ? "/admin" : "/vms";
    url.search = "";
    return NextResponse.redirect(url);
  }

  if (isAuthenticated && isAdminRoute && !isAdmin) {
    const url = request.nextUrl.clone();
    url.pathname = "/vms";
    url.search = "";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
