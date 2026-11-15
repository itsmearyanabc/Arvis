import { createHmac, timingSafeEqual } from "crypto";

/** token = <sequence_id>.<hmac_sha256_hex(sequence_id, UNSUBSCRIBE_SECRET)> */
export function makeUnsubscribeToken(sequenceId: string, secret = process.env.UNSUBSCRIBE_SECRET!): string {
  return `${sequenceId}.${createHmac("sha256", secret).update(sequenceId).digest("hex")}`;
}

export function verifyUnsubscribeToken(token: string, secret = process.env.UNSUBSCRIBE_SECRET): string | null {
  if (!secret) return null;
  const i = token.lastIndexOf(".");
  if (i <= 0) return null;
  const id = token.slice(0, i), sig = token.slice(i + 1);
  const expect = createHmac("sha256", secret).update(id).digest("hex");
  if (sig.length !== expect.length) return null;
  return timingSafeEqual(Buffer.from(sig, "hex"), Buffer.from(expect, "hex")) ? id : null;
}
