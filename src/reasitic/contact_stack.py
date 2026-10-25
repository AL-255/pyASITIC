"""i386 contact.index provenance from the earlier combined-driver entry ESP.

The original prepare-group prologue saves the prepare-contacts EBP. The next
builder has eight fewer argument bytes, so its uninitialized temporary index
aliases that saved word. No later contact or stack observation supplies it.
Addresses below follow 0x8050b2c/0x8051280 -> 0x8052c50 -> 0x8053580,
then the prepare-group (0x80536c8) and builder (0x8053a1c) prologues.
"""


def contact_frames(driver,entry_esp):
    if isinstance(entry_esp,bool)or not isinstance(entry_esp,int)or not 0<=entry_esp<=0xffffffff:raise ValueError('Driver ESP must be an unsigned i386 address')
    if driver=='pi2':
        esp=entry_esp-4-0x40-3*4  # saved EBP, locals, EDI/ESI/EBX
        esp-=3*4  # outstanding time, clone and matrix-constructor arguments
    elif driver=='calctrans':
        esp=entry_esp-4-0x54-3*4
        esp-=2*4  # both discretizer arguments
        esp+=8  # 0x80512a8 explicitly cleans up both arguments
        esp-=4  # matrix-constructor argument
    else:raise ValueError('Unsupported combined driver stack')
    esp-=4+8+3*4  # short flag/padding, frequency, reference/shape/output
    cap_entry=esp-4  # call return address
    esp=cap_entry-4-0x104-3*4  # CAP prologue
    esp-=2*4  # prepare-contacts arguments
    contacts_entry=esp-4
    frame=contacts_entry-4
    group_frame=frame-16-16-4-4
    builder_entry=frame-16-8-4
    return dict(cap_entry=cap_entry&0xffffffff,contacts_entry=contacts_entry&0xffffffff,
                contacts_frame=frame&0xffffffff,builder_entry=builder_entry&0xffffffff,
                index_address=group_frame&0xffffffff,index=frame&0xffffffff)
