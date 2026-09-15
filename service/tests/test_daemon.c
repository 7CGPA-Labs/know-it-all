#include <glib.h>
#include <libsoup/soup.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <sys/types.h>
#include <sys/wait.h>

static gboolean wait_for_daemon(SoupSession *session) {
    g_print("[*] Waiting for daemon HTTP server to start on port 5055...\n");
    for (int i = 0; i < 40; i++) {
        SoupMessage *msg = soup_message_new("GET", "http://127.0.0.1:5055/health");
        GError *error = NULL;
        GBytes *body = soup_session_send_and_read(session, msg, NULL, &error);
        if (body) {
            g_bytes_unref(body);
            g_object_unref(msg);
            g_print("[+] Daemon is ready!\n");
            return TRUE;
        }
        if (error) g_clear_error(&error);
        g_object_unref(msg);
        g_usleep(500000);
    }
    g_printerr("[!] Timed out waiting for daemon on port 5055!\n");
    return FALSE;
}

static gboolean test_health(SoupSession *session) {
    g_print("[TEST] GET /health ... ");
    SoupMessage *msg = soup_message_new("GET", "http://127.0.0.1:5055/health");
    GError *error = NULL;
    GBytes *body = soup_session_send_and_read(session, msg, NULL, &error);
    if (!body) {
        g_print("FAILED (HTTP request error: %s)\n", error ? error->message : "unknown");
        if (error) g_clear_error(&error);
        g_object_unref(msg);
        return FALSE;
    }

    guint status = soup_message_get_status(msg);
    if (status != 200) {
        g_print("FAILED (Status %u)\n", status);
        g_bytes_unref(body);
        g_object_unref(msg);
        return FALSE;
    }

    gsize size = 0;
    const char *data = g_bytes_get_data(body, &size);
    if (!strstr(data, "gedit-research-daemon-c")) {
        g_print("FAILED (Invalid response content)\n");
        g_bytes_unref(body);
        g_object_unref(msg);
        return FALSE;
    }

    g_print("PASSED\n");
    g_bytes_unref(body);
    g_object_unref(msg);
    return TRUE;
}

static gboolean test_render_md(SoupSession *session) {
    g_print("[TEST] POST /render-md ... ");
    SoupMessage *msg = soup_message_new("POST", "http://127.0.0.1:5055/render-md");
    const char *payload = "{\"markdown\": \"# Test Heading\\n* Test bullet\"}";
    GBytes *req_body = g_bytes_new(payload, strlen(payload));
    soup_message_set_request_body_from_bytes(msg, "application/json", req_body);
    g_bytes_unref(req_body);

    GError *error = NULL;
    GBytes *body = soup_session_send_and_read(session, msg, NULL, &error);
    if (!body || soup_message_get_status(msg) != 200) {
        g_print("FAILED (Status %u)\n", soup_message_get_status(msg));
        if (body) g_bytes_unref(body);
        if (error) g_clear_error(&error);
        g_object_unref(msg);
        return FALSE;
    }

    g_print("PASSED\n");
    g_bytes_unref(body);
    g_object_unref(msg);
    return TRUE;
}

static gboolean test_scrape_and_summarize(SoupSession *session) {
    g_print("[TEST] POST /scrape-and-summarize ... ");
    SoupMessage *msg = soup_message_new("POST", "http://127.0.0.1:5055/scrape-and-summarize");
    const char *payload = "{\"url\": \"https://example.com\", \"query\": \"test query\"}";
    GBytes *req_body = g_bytes_new(payload, strlen(payload));
    soup_message_set_request_body_from_bytes(msg, "application/json", req_body);
    g_bytes_unref(req_body);

    GError *error = NULL;
    GBytes *body = soup_session_send_and_read(session, msg, NULL, &error);
    if (!body || soup_message_get_status(msg) != 200) {
        g_print("FAILED (Status %u)\n", soup_message_get_status(msg));
        if (body) g_bytes_unref(body);
        if (error) g_clear_error(&error);
        g_object_unref(msg);
        return FALSE;
    }

    g_print("PASSED\n");
    g_bytes_unref(body);
    g_object_unref(msg);
    return TRUE;
}

int main(int argc, char *argv[]) {
    g_print("===========================================\n");
    g_print(" Running C Daemon Native HTTP Test Suite   \n");
    g_print("===========================================\n");

    pid_t daemon_pid = fork();
    if (daemon_pid == 0) {
        execl("./service/bin/daemon", "./service/bin/daemon", NULL);
        execl("./service/daemon", "./service/daemon", NULL);
        perror("execl daemon failed");
        exit(1);
    }

    SoupSession *session = soup_session_new();

    if (!wait_for_daemon(session)) {
        g_printerr("[!] Daemon failed to start within timeout period.\n");
        kill(daemon_pid, SIGTERM);
        waitpid(daemon_pid, NULL, 0);
        return 1;
    }

    gboolean ok = TRUE;
    ok = ok && test_health(session);
    ok = ok && test_render_md(session);
    ok = ok && test_scrape_and_summarize(session);

    g_object_unref(session);

    kill(daemon_pid, SIGTERM);
    waitpid(daemon_pid, NULL, 0);

    if (ok) {
        g_print("\n[+] All daemon C tests passed successfully!\n");
        return 0;
    } else {
        g_print("\n[!] One or more C tests failed!\n");
        return 1;
    }
}
