import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useLoaderData, useRevalidator } from "react-router";

import { api, errorMessage, type ChatRole, type MessageOut } from "../../lib/api/client";
import { useChatSocket, type ChatEvent } from "../../lib/useChatSocket";
import ui from "../../styles/ui.module.css";
import c from "./chat.module.css";
import PushPrompt from "./PushPrompt";
import type { chatLoader } from "../loaders";

const MAX_LENGTH = 1000;
const TYPING_SHOWN_MS = 3000; // sin nuevos avisos, "escribiendo…" desaparece
const TYPING_NOTIFY_EVERY_MS = 2000; // como mucho un aviso de "escribiendo" cada tanto

/** Las dos conversaciones por tu papel en cada una; la de giver es null hasta revelar. */
type Conversations = { receiver: MessageOut[]; giver: MessageOut[] | null };

function unreadCount(messages: MessageOut[] | null): number {
  return messages?.filter((m) => !m.mine && !m.read_at).length ?? 0;
}

/**
 * Chat con dos pestañas: "quien te regala" (anónimo para ti) y "a quien regalas".
 * El loader trae el historial; a partir de ahí todo llega por el websocket (mensajes,
 * leídos y "escribiendo…") y se guarda en estado local. Enviar y marcar leído van por REST.
 */
export default function Chat() {
  const data = useLoaderData<typeof chatLoader>();
  const { me, receiverName } = data;
  const slug = me.group.slug;
  const [tab, setTab] = useState<ChatRole>("receiver");

  const [conversations, setConversations] = useState<Conversations>({
    receiver: data.asReceiver,
    giver: data.asGiver,
  });
  // Si el loader vuelve a ejecutarse (p. ej. tras reconectar), su historial manda.
  const [loaded, setLoaded] = useState(data);
  if (loaded !== data) {
    setLoaded(data);
    setConversations({ receiver: data.asReceiver, giver: data.asGiver });
  }

  const [typing, setTyping] = useState<ChatRole | null>(null);
  const typingTimer = useRef(0);

  function update(role: ChatRole, change: (messages: MessageOut[]) => MessageOut[]) {
    setConversations((prev) => ({ ...prev, [role]: prev[role] ? change(prev[role]) : null }));
  }

  function handleEvent(event: ChatEvent) {
    if (event.type === "message") {
      update(event.role, (messages) => [...messages, event.message]);
      if (event.role === typing) setTyping(null);
    } else if (event.type === "read") {
      const now = new Date().toISOString();
      update(event.role, (messages) => messages.map((m) => (m.mine ? { ...m, read_at: now } : m)));
    } else if (event.type === "typing") {
      setTyping(event.role);
      clearTimeout(typingTimer.current);
      typingTimer.current = window.setTimeout(() => setTyping(null), TYPING_SHOWN_MS);
    }
  }

  const { revalidate } = useRevalidator();
  const { sendTyping } = useChatSocket(slug, handleEvent, revalidate);

  // Al mirar una pestaña con mensajes sin leer (o al llegar uno nuevo a la que miras)
  // se marcan como leídos en la API y en local.
  const messages = conversations[tab];
  // Los avisos se ofrecen cuando ya te han escrito: ahí se entiende para qué sirven.
  const hasReceivedSomething = Object.values(conversations).some((list) =>
    list?.some((m) => !m.mine),
  );
  useEffect(() => {
    if (unreadCount(messages) === 0) return;
    api
      .POST("/groups/{slug}/chat/{role}/read", { params: { path: { slug, role: tab } } })
      .then(() => {
        const now = new Date().toISOString();
        setConversations((prev) => ({
          ...prev,
          [tab]: prev[tab]?.map((m) => (m.mine || m.read_at ? m : { ...m, read_at: now })) ?? null,
        }));
      });
  }, [slug, tab, messages]);

  return (
    <main className={`${ui.page} ${c.screen}`}>
      <header className={c.head}>
        <Link to={`/g/${slug}`} className={ui.logo}>
          psst
        </Link>
        <div className={c.tabs} role="tablist">
          <Tab
            role="receiver"
            current={tab}
            unread={unreadCount(conversations.receiver)}
            onSelect={setTab}
          >
            quien te regala
          </Tab>
          <Tab role="giver" current={tab} unread={unreadCount(conversations.giver)} onSelect={setTab}>
            a quien regalas
          </Tab>
        </div>
        <Who tab={tab} receiverName={receiverName} />
      </header>

      {messages === null ? (
        <section className={ui.block}>
          <p className={ui.hint}>
            Para escribirle, antes tienes que descubrir a quién le regalas.
          </p>
          <Link to={`/g/${slug}/revelado`} className={ui.button}>
            abrir la celosía
          </Link>
        </section>
      ) : (
        <>
          <Messages messages={messages} anonymous={tab === "receiver"} typing={typing === tab} />
          {hasReceivedSomething && <PushPrompt slug={slug} />}
          <Composer
            slug={slug}
            role={tab}
            onTyping={() => sendTyping(tab)}
            onSent={(message) => update(tab, (list) => [...list, message])}
          />
        </>
      )}
    </main>
  );
}

function Tab({
  role,
  current,
  unread,
  onSelect,
  children,
}: {
  role: ChatRole;
  current: ChatRole;
  unread: number;
  onSelect: (role: ChatRole) => void;
  children: string;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={role === current}
      onClick={() => onSelect(role)}
    >
      {children}
      {unread > 0 && <span className={c.badge}>{unread}</span>}
    </button>
  );
}

/** Con quién hablas. Quien te regala es una ventanita de celosía: ni nombre ni inicial. */
function Who({ tab, receiverName }: { tab: ChatRole; receiverName: string | null }) {
  if (tab === "receiver") {
    return (
      <div className={c.who}>
        <AnonymousAvatar />
        <div>
          <strong>tu amigo invisible</strong>
          <span>no sabes quién es. sí sabe quién eres tú.</span>
        </div>
      </div>
    );
  }
  return (
    <div className={c.who}>
      {receiverName && <NamedAvatar name={receiverName} />}
      <div>
        <strong>{receiverName ?? "a quien regalas"}</strong>
        <span>no sabe que eres tú</span>
      </div>
    </div>
  );
}

function AnonymousAvatar() {
  return (
    <span className={c.anonymous} aria-label="anónimo">
      <i className={ui.lattice} />
    </span>
  );
}

function NamedAvatar({ name }: { name: string }) {
  return (
    <span className={c.named} aria-hidden="true">
      {[...name][0]?.toUpperCase()}
    </span>
  );
}

function Messages({
  messages,
  anonymous,
  typing,
}: {
  messages: MessageOut[];
  anonymous: boolean;
  typing: boolean;
}) {
  const listRef = useRef<HTMLDivElement>(null);
  const last = messages[messages.length - 1];

  // Siempre abajo del todo, donde está lo último.
  useEffect(() => {
    const list = listRef.current;
    if (list) list.scrollTop = list.scrollHeight;
  }, [messages, typing]);

  return (
    <div ref={listRef} className={c.messages} aria-live="polite">
      {messages.length === 0 && (
        <p className={c.empty}>
          {anonymous
            ? "Aquí puedes contestar a quien te regala. No sabrás quién es."
            : "Pregúntale lo que quieras. No sabrá que eres tú."}
        </p>
      )}
      {messages.map((m) => (
        <div key={m.id} className={m.mine ? `${c.message} ${c.mine}` : c.message}>
          {!m.mine && (anonymous ? <AnonymousAvatar /> : <span className={c.spacer} />)}
          <p>{m.body}</p>
        </div>
      ))}
      {typing && (
        <div className={`${c.message} ${c.typing}`} aria-label="escribiendo">
          {anonymous ? <AnonymousAvatar /> : <span className={c.spacer} />}
          <p>
            <i />
            <i />
            <i />
          </p>
        </div>
      )}
      {!typing && last?.mine && last.read_at && (
        <span className={c.read}>
          <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
            <path
              d="M1.5 8.5l3 3 6-7M7 11.5l1 1 6-8"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          leído
        </span>
      )}
    </div>
  );
}

function Composer({
  slug,
  role,
  onTyping,
  onSent,
}: {
  slug: string;
  role: ChatRole;
  onTyping: () => void;
  onSent: (message: MessageOut) => void;
}) {
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const lastTypingNotice = useRef(0);

  function handleChange(value: string) {
    setText(value);
    const now = Date.now();
    if (value && now - lastTypingNotice.current > TYPING_NOTIFY_EVERY_MS) {
      lastTypingNotice.current = now;
      onTyping();
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const body = text.trim();
    if (!body) return;
    setSending(true);
    setError(null);
    const { data, error } = await api.POST("/groups/{slug}/chat/{role}/messages", {
      params: { path: { slug, role } },
      body: { body },
    });
    setSending(false);

    if (data) {
      setText("");
      lastTypingNotice.current = 0;
      onSent(data);
    } else {
      setError(errorMessage(error));
    }
  }

  return (
    <form className={c.composer} onSubmit={handleSubmit}>
      {error && (
        <p className={ui.error} role="alert">
          {error}
        </p>
      )}
      <div className={c.composerRow}>
        <input
          className={ui.input}
          value={text}
          onChange={(event) => handleChange(event.target.value)}
          maxLength={MAX_LENGTH}
          placeholder="escribe algo…"
          aria-label="mensaje"
          autoComplete="off"
        />
        <button type="submit" className={c.send} aria-label="enviar" disabled={sending}>
          <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
            <path
              d="M3 10h13M11 4.5L16.5 10 11 15.5"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </div>
    </form>
  );
}
