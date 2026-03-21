/**
 * Recursively traverses open shadow roots and returns all elements
 * matching the given CSS selector.
 */
export function queryShadowAll<T extends Element = Element>(
  root: Element | Document | ShadowRoot,
  selector: string
): T[] {
  const results: T[] = [];
  const stack: (Element | Document | ShadowRoot)[] = [root];

  while (stack.length > 0) {
    const current = stack.pop()!;

    // Query this level
    const found = Array.from(current.querySelectorAll<T>(selector));
    results.push(...found);

    // Descend into shadow roots of all children
    const children = Array.from(current.querySelectorAll('*'));
    for (const child of children) {
      if (child.shadowRoot) {
        stack.push(child.shadowRoot);
      }
    }
  }

  return results;
}
