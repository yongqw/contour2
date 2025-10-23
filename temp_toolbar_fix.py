# Enhanced toolbar configuration for high DPI support
        try:
            # Scale toolbar icon size if possible
            toolbar_size = max(int(20 * self.scale_factor), 24)

            # Try to configure toolbar for better DPI support
            # 1. Try to set icon size (may not work on all matplotlib versions)
            for toolbar_item in self.toolbar.toolitems:
                if hasattr(toolbar_item, 'set_iconsize'):
                    try:
                        toolbar_item.set_iconsize(toolbar_size)
                    except:
                        pass

            # 2. Update toolbar layout
            self.toolbar.update()

            # 3. Try to set DPI awareness on figure window
            try:
                self.canvas.manager.set_window_title("Contour View")
                # Try to set window DPI awareness (matplotlib 3.7+)
                if hasattr(self.canvas.manager, 'window'):
                    self.canvas.manager.window.tk.call('tk', 'scaling', 1.0)
            except Exception as e:
                print(f"DEBUG: Toolbar DPI scaling attempt: {e}")
                pass  # Toolbar might not support all scaling options

            # 4. Manual toolbar button enhancement if needed
            # Some matplotlib versions don't support toolbar icon scaling
            if self.scale_factor > 1.5:
                try:
                    # Force larger icons by modifying toolbar properties
                    for child in toolbar_frame.winfo_children():
                        if isinstance(child, tk.Button):
                            # Try to make button text larger
                            font_size = max(int(10 * self.scale_factor), 12)
                            child.configure(font=("Arial", font_size))
                except:
                    pass

        except Exception as e:
            print(f"DEBUG: Toolbar configuration failed: {e}")
            pass  # Continue even if toolbar scaling fails