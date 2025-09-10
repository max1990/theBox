def wrap360(x: float)->float:
    return (x%360.0+360.0)%360.0

def to_true_bearing(a:float,h:float,zero_axis='forward',positive='cw')->float:
    adj=a if positive=='cw' else -a
    if zero_axis=='right': adj+=90
    elif zero_axis=='left': adj-=90
    elif zero_axis=='rear': adj+=180
    return wrap360(h+adj)
