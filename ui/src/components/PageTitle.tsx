/** Name the window after the screen; React places the title in the document head. */
export function PageTitle({ children }: { children: string }) {
  return <title>{`${children} · Court Booker`}</title>;
}
